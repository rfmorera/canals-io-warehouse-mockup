# Requirements Document

## Introduction

A backend service for an e-commerce platform that exposes a minimal order management API. The service accepts order creation requests from a UI, selects the optimal warehouse to fulfill the order based on product availability and proximity to the shipping address, and processes payment via an external payment provider. The system must scale to millions of products and warehouses while maintaining response times of 3–5 seconds.

## Glossary

- **Order_Service**: The Flask-based backend service that handles order creation and orchestration.
- **Order**: A record containing a customer reference, a shipping address, and one or more line items (product + quantity).
- **Line_Item**: A single entry in an order specifying a product and the requested quantity.
- **Warehouse**: A physical location that holds inventory of products, identified by a geographic coordinate.
- **Inventory**: The stock of a specific product held at a specific warehouse.
- **Geocoder**: A mocked external service that converts a shipping address string into a latitude/longitude coordinate pair.
- **Payment_Gateway**: A mocked external service that charges a credit card given a card number, amount, and description.
- **Customer_Payment_Store**: A mocked service that retrieves stored payment information (credit card number) for a given `customer_id`. Represents a real-world payment vault or tokenization service.
- **Warehouse_Selector**: The internal component responsible for finding the optimal warehouse to fulfill an order.
- **Candidate_Warehouse**: A warehouse that has sufficient inventory for all line items in an order.
- **Expanding_Radius_Search**: A strategy that queries warehouses in progressively larger distance bands (measured in miles) from the shipping address, stopping as soon as a qualifying warehouse is found.
- **Manufacturer_Country**: The ISO 3166-1 alpha-2 country code of a product's manufacturer (e.g. `"US"`, `"DE"`), stored on the product record.
- **Country_Filter**: An optional order-level preference specifying a list of manufacturer country codes. When provided, only products whose manufacturer country is in the list are eligible. When omitted or null, no restriction applies.


## Requirements

### Requirement 1: Order Creation Endpoint

**User Story:** As a customer, I want to place an order through the UI using my customer ID, so that my stored payment information is used and I never need to send card details in the request.

#### Acceptance Criteria

1. WHEN a POST request is received at `/orders` with a valid order payload, THE Order_Service SHALL create an order record and return a 201 response containing the order ID and assigned warehouse ID.
2. WHEN a POST request is received at `/orders`, THE Order_Service SHALL validate that the payload contains a non-empty `customer_id`, a shipping address, and at least one line item.
3. IF the request payload is missing required fields or contains invalid data, THEN THE Order_Service SHALL return a 400 response with a descriptive error message identifying the invalid field.
4. THE Order_Service SHALL complete the full order creation flow (geocoding, warehouse selection, payment info lookup, payment) within 5 seconds under normal operating conditions.

---

### Requirement 2: Order Data Model

**User Story:** As a developer, I want a well-defined order schema, so that order data is stored consistently and can be queried reliably.

#### Acceptance Criteria

1. THE Order_Service SHALL persist each order with the following fields: a unique order ID, customer identifier, shipping address string, shipping latitude, shipping longitude, list of line items, assigned warehouse ID, payment status, and creation timestamp.
2. THE Order_Service SHALL persist each line item with a product identifier and an integer quantity greater than zero.
3. IF a line item quantity is less than or equal to zero, THEN THE Order_Service SHALL return a 400 response with a descriptive error message.

---

### Requirement 3: Geocoding

**User Story:** As the system, I want to convert a shipping address to coordinates, so that warehouse proximity can be calculated.

#### Acceptance Criteria

1. WHEN an order is created, THE Geocoder SHALL convert the shipping address string into a latitude/longitude coordinate pair before warehouse selection begins.
2. IF the Geocoder returns an error or cannot resolve the address, THEN THE Order_Service SHALL return a 422 response with a message indicating the address could not be geocoded.
3. THE Geocoder SHALL be implemented as a mockable interface so that a real geocoding provider can be substituted without changing Order_Service logic.


---

### Requirement 4: Warehouse Selection — Availability Check

**User Story:** As the system, I want to find a warehouse that can fulfill all items in an order, so that the order can be shipped from a single location.

#### Acceptance Criteria

1. WHEN selecting a warehouse, THE Warehouse_Selector SHALL only consider warehouses where every line item in the order has available inventory greater than or equal to the requested quantity.
2. THE Warehouse_Selector SHALL evaluate warehouses using the Expanding_Radius_Search strategy, querying in progressively larger distance bands (in miles) from the shipping coordinates.
3. WHEN a Candidate_Warehouse is found within the current search radius, THE Warehouse_Selector SHALL stop expanding the radius and select that warehouse without querying farther warehouses.
4. IF multiple Candidate_Warehouses exist within the same distance band, THE Warehouse_Selector SHALL select the one with the shortest geodesic distance to the shipping coordinates.
5. IF no Candidate_Warehouse is found after exhausting all search bands, THEN THE Order_Service SHALL return a 422 response with a message indicating no warehouse can fulfill the order.

---

### Requirement 5: Warehouse Selection — Scale and Efficiency

**User Story:** As a platform operator, I want warehouse selection to be efficient at scale, so that the system performs acceptably with millions of products and warehouses.

#### Acceptance Criteria

1. THE Warehouse_Selector SHALL use native geospatial index queries to filter warehouses by distance, avoiding full-table scans.
2. THE Warehouse_Selector SHALL check inventory availability for a batch of warehouses in a single database query per distance band, rather than issuing one query per warehouse.
3. THE Order_Service SHALL use a database that natively supports geospatial indexing and efficient radius queries (e.g., PostGIS on PostgreSQL).
4. WHILE processing an order, THE Order_Service SHALL not issue more database round-trips than the number of distance bands searched plus two (one for order persistence, one for inventory reservation).

---

### Requirement 6: Inventory Reservation

**User Story:** As the system, I want to reserve inventory when an order is placed and only commit the deduction after successful payment, so that stock is not permanently removed for orders that fail payment.

#### Acceptance Criteria

1. WHEN a warehouse is selected, THE Order_Service SHALL increment the `reserved_qty` of each ordered product at that warehouse by the ordered quantity within a single atomic transaction, without modifying `available_qty`.
2. THE Warehouse_Selector SHALL treat a product as available only when `available_qty - reserved_qty >= requested quantity`, ensuring reserved stock is not double-allocated.
3. WHEN the Payment_Gateway returns a success response, THE Order_Service SHALL decrement `available_qty` and decrement `reserved_qty` by the ordered quantity in a single atomic transaction, finalizing the stock deduction.
4. IF the Payment_Gateway returns a failure response, THEN THE Order_Service SHALL decrement `reserved_qty` by the ordered quantity to release the reservation, leaving `available_qty` unchanged.
5. IF a concurrent order causes `available_qty - reserved_qty` to drop below the required quantity before the reservation commits, THEN THE Order_Service SHALL retry warehouse selection before returning an error.
6. THE Order_Service SHALL use row-level locking on the relevant `warehouse_inventory` rows during reservation to prevent race conditions under concurrent order creation.


---

### Requirement 7: Customer Payment Information Lookup

**User Story:** As the system, I want to retrieve a customer's stored payment information using their customer ID, so that card details are never transmitted in the order request.

#### Acceptance Criteria

1. WHEN processing an order, THE Order_Service SHALL call the Customer_Payment_Store with the `customer_id` to retrieve the stored credit card number before calling the Payment_Gateway.
2. IF the Customer_Payment_Store returns no payment information for the given `customer_id`, THEN THE Order_Service SHALL return a 422 response with a message indicating no payment method is on file for the customer.
3. THE Customer_Payment_Store SHALL be implemented as a mockable interface so that a real payment vault or tokenization provider can be substituted without changing Order_Service logic.
4. THE Order_Service SHALL NOT accept or store a raw credit card number in the order request payload.

---

### Requirement 8: Payment Processing

**User Story:** As a customer, I want my payment to be charged when I place an order, so that the transaction is completed at the time of purchase.

#### Acceptance Criteria

1. WHEN a warehouse is selected and inventory is reserved, THE Order_Service SHALL retrieve the customer's credit card number from the Customer_Payment_Store and call the Payment_Gateway with the card number, total order amount, and a human-readable order description.
2. WHEN the Payment_Gateway returns a success response, THE Order_Service SHALL record the payment status as "paid" on the order record.
3. IF the Payment_Gateway returns a failure response, THEN THE Order_Service SHALL release the reserved inventory, mark the order as "payment_failed", and return a 402 response with the payment failure reason.
4. THE Payment_Gateway SHALL be implemented as a mockable interface so that a real payment provider can be substituted without changing Order_Service logic.

---

### Requirement 9: Containerized Deployment

**User Story:** As a developer, I want the service to run in Docker, so that the environment is reproducible and easy to deploy.

#### Acceptance Criteria

1. THE Order_Service SHALL be packaged as a Docker image that starts the Flask application on a configurable port.
2. THE Order_Service SHALL provide a Docker Compose file that starts the Order_Service container and the database container together with a single `docker compose up` command.
3. THE Order_Service SHALL read all external configuration (database URL, port) from environment variables.
4. IF a required environment variable is missing at startup, THEN THE Order_Service SHALL log a descriptive error message and exit with a non-zero status code.

---

### Requirement 10: Manufacturer Country Filter

**User Story:** As a customer, I want to optionally restrict my order to products manufactured in specific countries, so that I can support preferred supply chains across any market.

#### Acceptance Criteria

1. THE Order_Service SHALL accept an optional `manufacturer_countries` field in the order payload, which may contain one or more ISO 3166-1 alpha-2 country codes (e.g. `["US", "DE"]`).
2. IF `manufacturer_countries` is omitted or null, THEN THE Order_Service SHALL apply no country restriction and consider all products regardless of manufacturer country.
3. IF `manufacturer_countries` is provided, THEN THE Warehouse_Selector SHALL only consider warehouses where every line item in the order is stocked with a product whose `manufacturer_country` matches one of the specified codes.
4. IF `manufacturer_countries` contains a value that is not a valid ISO 3166-1 alpha-2 code, THEN THE Order_Service SHALL return a 400 response with a descriptive error message identifying the invalid value.
5. IF no warehouse can fulfill the order given the country restriction, THEN THE Order_Service SHALL return a 422 response indicating no warehouse can fulfill the order with the requested manufacturer countries.

---

### Requirement 11: Error Handling and Observability

**User Story:** As a developer, I want consistent error responses and structured logs, so that I can diagnose issues in production.

#### Acceptance Criteria

1. THE Order_Service SHALL return all error responses as JSON objects with at least an `error` field containing a human-readable message.
2. WHEN an unhandled exception occurs, THE Order_Service SHALL log the full stack trace at ERROR level and return a 500 response with a generic error message that does not expose internal details.
3. WHEN an order is successfully created, THE Order_Service SHALL emit a structured log entry at INFO level containing the order ID, selected warehouse ID, and total processing time in milliseconds.
