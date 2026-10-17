To wrap up this workshop, we have created a simple simulation of an airport.
The basic simulation is in the 'plain' database. The data in each of the other
four databases show the results of a shock to the system. Your mission is to
write some SQL queries to figure out what one of those shocks was. The tables
in each database are:

| table     | field               | type     | purpose                           |
| :-------- | :------------------ | :------- | :-------------------------------- |
| airline   | airline_id          | text     | primary key                       |
|           | name                | text     | airline name                      |
| flight    | flight_id           | text     | primary key                       |
|           | airline_id          | text     | foreign key                       |
|           | origin              | text     | city the flight arrives from      |
|           | destination         | text     | city the flight departs to        |
|           | sched_arrival       | datetime | scheduled arrival time            |
|           | actual_arrival      | datetime | actual arrival time               |
|           | sched_departure     | datetime | scheduled departure time          |
|           | actual_departure    | datetime | actual departure time             |
|           | arrival_delay_min   | real     | arrival delay in minutes          |
|           | departure_delay_min | real     | departure delay in minutes        |
|           | capacity            | bigint   | seat capacity                     |
| passenger | passenger_id        | text     | primary key                       |
|           | family              | text     | surname                           |
|           | personal            | text     | forename                          |
|           | kind                | text     | originating/connecting/terminating|
|           | origin              | text     | city the journey starts at        |
|           | destination         | text     | city the journey ends at          |
|           | arrival_flight_id   | text     | flight they arrived on (nullable) |
|           | departure_flight_id | text     | flight they depart on (nullable)  |
|           | arrived_at          | datetime | when they reached the airport     |
|           | departed_at         | datetime | when they left the airport        |
| mishap    | mishap_id           | text     | primary key                       |
|           | passenger_id        | text     | foreign key                       |
|           | missed_flight_id    | text     | flight they missed                |
|           | rebooked_flight_id  | text     | flight they were moved to         |
|           | reason              | text     | missed or bumped                  |
|           | occurred_at         | datetime | when the mishap happened          |
|           | wait_min            | real     | how long they waited in minutes   |

Note that the delay and wait columns could be calculated from the other times,
but are provided here to keep your queries simpler.
