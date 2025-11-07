# 2025-11-14


# 2025-11-07

feedback:

1. demand: merge demand route and vehicle
   trip into one
2. demand: demand od add zone_id_from, zone_id_to
3. demand: create demand zone table
4. network: node change x and y to lon and lat
5. Network: link:
   https://wiki.openstreetmap.org/wiki/Key:priority_road

### Question: why we need elevation field?

Signal:

Controller

    controller_id

PhasePlans
SigID
PhasePlanID
MinGreen1 -- an 16-item array
MinGreen2 -- an 16-item array
Max1 -- an 16-item array
Max2 -- an 16-item array
Max3 -- an 16-item array
Walk -- an 16-item array
Walk2 -- an 16-item array
PedClear -- an 16-item array
PedClear2 -- an 16-item array
Passage (VehExtention) -- an 16-item array
Yellow -- an 16-item array
RedClear -- an 16-item array
Options
Min Veh Recall
Max Veh Recall
Soft Veh Recall
Ped Recall
Dual Entry

Sequence
SeqID
PhaseID
Ring
Barrier
Position

Coordination
SigID
PatternID
Coord Mode (Actuated Coord, Auto permissive, fixed permissive, etc.)
Force Off
Max Mode
Correction Mode (Dwell, addonly, smooth, shortway, shortway2, etc.)
Offset Reference
PhasePlanID
SeqID
CycleTime
OffsetTime
VehDetPlanID
PedDetPlanID

Split
SplitID
SplitTime -- 16-item array (?)
CoordinatedPhase -- 16-item array (?)
ForceOffMode -- 16-item array (?)
Reference Point

VehDetector
SigID
VehDetPlanID
VehDetID
CallPhase
Call Overlap?
Extend?
Delay?

PedDetector
SigID
PedDetPlanID
PedDetID
CallPhase
Call Overlap?
Extend?
Delay?

Overlap?
OverlapPlanID
OverlapID
IncludedPhases

Schedule
ScheduleID
DayPlanID
Month -- 12-item array
DOW -- 7-item array
DOM -- 31-item array

DayPlan
DayPlanID
EventID
StartTime (HH:MM)
ActionID

Action
ActionID
PatternID

# 2025-10-31

Schema

* [X] combine lane_type and acce_mode in sql

Network

* [X] lane table: Add geom for lane table
* [X] link table: is_one_way remove
* [X] movement table: add node_id in movement
* [X] Link table: bearning

Demand

* [X] turning_flow table: change volume to flow
* [X] turning flow table:turn_ratio to flow
* [X] turning flow table: remove movement id
* [X] turning flow table:add from_link_id
* [X] turning flow table:add to_link_id
* [X] turning flow table: remove time_slice
* [X] turning flow table: remove at_time
* [X] turning flow table: add veh_type
* [X] Link table: bearning
* [X] OD
  Date
  Day of week
  Day_type: weekend / weekday
  from_time : HH:MM
  to_time

Trajectory:
