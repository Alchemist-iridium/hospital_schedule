# Goal

Create incentives for the workers to gain priority upon current sequence by choosing certain shifts and redeeming the points gained.
The current schedule sequence is based on a fixed priority list, which is the initial_order for worker. Pay attention that the sequences are separated for senior and junior workers.

The process of the system consists of two stages.

1: In-group and type based sign-up sequence generation
- For the next week's schedule (the sign-up sequences of the senior and junior workers are separated).
- Choose workgroup - (publish in group initial order by admin) - priority score

2: The schedule sign up process
- Demand updated from customer: Right now the system is a weekly signup system but the customer would like to have a monthly signup system. Although the system could be updated to perform the functions, I recommend to implement the system

# Roles
- worker
	- type: senior and junior, comes with different requirements on the workgroup limit
	- two factors decide the sequence in choosing the schedule
		- initial_order: the current fixed sequence of schedule sign-up
		- points redeemed
- admin
	- suggested id: 0000, as it is used for the notification for the admin
# Packages used

```
pip install flask flask-sqlalchemy werkzeug flask-login pandas openpyxl
```


# Demonstration of the process

## Add admin
- run create_admin.py
suggested id: 0000

## Run the program
- run app.py and login
![[截屏2025-04-02 13.17.46.png]]

## Data Management on Admin dashboard
- manage data: manage worker, interval, shift, workgroup, shift-interval relationship
- operation log: record for important operations
- sample file in test_file folder
- (shift and interval are similar, the shift-interval relationship connects the shift, interval and workgroup. The shift_interval_generator is designed for a week's relationship)
![[截屏2025-04-02 13.18.36.png]]

workers

![[截屏2025-04-02 13.23.42.png]]![[截屏2025-04-02 13.25.46.png]]
![[截屏2025-04-02 13.28.56.png]]
![[截屏2025-04-02 13.29.14.png]]
Interval: the basic unit component for workgroups. The maximum number of senior/junior workers working at a time in work group is set here.
![[截屏2025-04-02 13.45.38.png]]
Shift: points can be modifed as the weekends are different for each month
![[截屏2025-04-02 13.53.05.png]]
Work group (each month the worker is going to choose one from the four work group. The limits on the number of people in the workgroup is limited here.)
![[截屏2025-04-02 14.00.22.png]]

Shift interval relationship, which connects the interval (as basic units for shift) with shift for each workgroup.

![[截屏2025-04-02 14.02.22.png]]


## Initial schedule sign-up process

### overall process
#### workgroup choice
- worker: dashboard - workgroup selection
	- choose workgroup, only available choice allowed.
![[截屏2025-04-02 14.14.10.png]]
![[截屏2025-04-02 14.14.58.png]]
![[截屏2025-04-02 14.16.43.png]]
![[截屏2025-04-02 14.17.51.png]]

- admin: on dashboard - workgroup registration
	- notify all unregistered workers if there is anyone who is supposed to have a workgroup but is not.
	- publish in-group initial order, compulsory for the next step


#### redeem points for priority
Requirement:
admin publish in-group order initial orders in workgroup registration.

![[截屏2025-04-02 14.21.09.png]]

worker:
- receive notification
- view in-group sequence
- redeem points to adjust the sequence

![[截屏2025-04-02 14.23.34.png]]![[截屏2025-04-02 14.24.17.png]]
worker A
![[截屏2025-04-02 14.24.56.png]]

- Real time sequence adjustment with point redeem 
worker B as an example
![[截屏2025-04-02 14.26.19.png]]![[截屏2025-04-02 14.27.15.png]]

- Other's sequence (worker A) will also be adjusted.
![[截屏2025-04-02 14.28.07.png]]


#### admin confirm final sequence

schedule sequence is fixed, sequence file is exported and workers can choose the schedule
![[截屏2025-04-02 14.30.53.png]]![[截屏2025-04-02 14.31.16.png]]


#### worker chooses the shift
![[截屏2025-04-02 15.22.42.png]]

- conflict is prevented in real time
![[截屏2025-04-02 15.19.29.png]]
not available after submitting
![[截屏2025-04-02 15.25.04.png]]

- worker dashboard- your schedule
![[截屏2025-04-02 15.23.38.png]]


- next worker is notified
![[截屏2025-04-02 15.26.47.png]]


- only available shift for choice
![[截屏2025-04-02 15.37.28.png]]


#### admin export final schedule

- admin will be notified when all senior/junior in a workgroup have chosen their schedule

![[截屏2025-04-02 15.42.50.png]]

export the schedule
![[截屏2025-04-02 16.13.23.png]]
by worker

![[截屏2025-04-02 15.55.42.png]]

by shift

![[截屏2025-04-02 15.56.15.png]]


in spreadsheet
worker name (along with the workgroup they choose)


![[截屏2025-04-02 16.13.55.png]]



#### special events & clear up for next scheduling

manually update the points if there are special events such as shift swipe and absence

![[截屏2025-04-02 16.15.24.png]]

!!! Reset schedule before the next scheduling process!!!