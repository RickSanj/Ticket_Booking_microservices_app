# Ticket Booking System – Microservices Architecture

## Overview
This project is a microservices-based ticket booking system, designed for scalability, maintainability, and fault tolerance. It allows users to register, log in, browse events, select seats, and make bookings with secure payments.
<br>
Built with Docker, Kafka, Redis, Cassandra, Postgres, Consul. The system consists of independent services that communicate through REST APIs and asynchronous messaging using Kafka.

## Requirements
### Functional Requirements
1. User Authentication & Authorization.<br>
- Users must be able to register, log in, and receive a session id. <br>
- Role-based access: Admins can create events; users can book. <br>
2. Event Management <br>
- Admins can create, update, and delete events. <br>
- All users can view events, including metadata like date, location, and ticket types. <br>
3. Booking Service <be>
- Must provide real-time seat availability for the selected event. <br>
- Users can select and lock seats during booking to avoid overbooking. <br>
4. Payment Processing (Simulates payment processing) <br>
- The system initiates a payment request. <br>
- Payment service verifies transaction (mock) and returns success/failure. <br>
- On success, the seat is permanently locked and booking status is updated. <br>
5. Event-Driven Notifications <br>
- Emit events such as BookingCreated, PaymentConfirmed, BookingCancelled via Kafka. <br>
- Consumers act accordingly (e.g., Payment Service listens to booking events). <br>
6. API Gateway <br>
- Route external requests to proper services. <br>
- Validate session id and forward headers to downstream services. <br>

### Nonfunctional Requirements
1. Consistency <br>
-  Strong consistency for booking: Once a seat is locked by a user, it must not be available for others. <br>
-  Eventual consistency: Payment status must align with booking state. (BookingCreated → Kafka → PaymentService → emits PaymentConfirmed or PaymentFailed) <br>
2. Availability & Fault Tolerance
- High availability for viewing events.
- System should continue operating even if one service is down (except critical ones like auth or payment).

## Kafka Communication Flow
message: booking_created; <br>
produced by: Booking Service; <br>
consumed by: Payment Service; <br>
purpose: Notify payment service that a booking has been created and needs payment.<br>
<br>
message: payment_processed;<br>
produced by: Payment Service;<br>	
consumed by: Booking Service;<br>	
purpose: Confirm that a payment was successful or failed, triggering booking status update.<br>

<img width="966" alt="image" src="https://github.com/user-attachments/assets/89d51c0f-1c54-4953-9937-1c4f8b725db6" />



## PORTS:
api-gateway 8080 <br>
event-service 8082<br>
booking-service 8084, 8085, 8086<br>
payment-service 8087, 8088<br>

consul 8500<br>
postgres 5432<br>


## How to run
1. **Clone repo**
```bash
    git clone <repository-url>
    cd <repository-folder>
```
2. **Build project in docker**
```bash
docker-compose build --no-cache 
```
3. **Run Docker compose**
```bash
docker compose up 
```
