from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from math import pi as Pi
import math
import pygame
from time import sleep

HOMEBT=0
WHEELAX=0
SPEEDAXIS=1

# ==========================================================
#                  INITIALIZATION FUNCTIONS
# ==========================================================
def init_sim():
    client = RemoteAPIClient()
    sim = client.require('sim')
    sim.setStepping(True)

    # handles
    car = sim.getObject('/Car')
    carLeftMotor = sim.getObject('/Car/lb_motor')
    carRightMotor = sim.getObject('/Car/rb_motor')
    car_right_axel = sim.getObject('/Car/front_right_axel')
    car_left_axel = sim.getObject('/Car/front_left_axel')

    front_sensor = sim.getObject('/Car/front_sensor')

    ref_points = [
        sim.getObject('/ref_1'),
        sim.getObject('/ref_2'),
        sim.getObject('/ref_3'),
        sim.getObject('/ref_4')
    ]
    for ref in ref_points:
        sim.setShapeColor(ref, None, sim.colorcomponent_ambient_diffuse, [1, 0, 0])

    park_1 = sim.getObject('/park_1')
    park_2 = sim.getObject('/park_2')
    
    #TUI vars
    mode = "MANUAL"

    return sim, car, carLeftMotor, carRightMotor, car_left_axel, car_right_axel, front_sensor, ref_points, park_1, park_2, mode


def init_pygame():
    pygame.init()
    pygame.display.set_mode((128, 72))


# ==========================================================
#                     INPUT HANDLING
# ==========================================================
def read_inputs(angle, velocity, mode, stop, joystick):
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                stop = True
                
            if event.key == pygame.K_m:
                mode = "MANUAL"
                velocity = 0
            
            if event.key == pygame.K_p:
                velocity = 1
                mode = "PARKING"
                
            if event.key == pygame.K_n:
                velocity = 2
                mode = "AUTO"

            if mode == "MANUAL":
                if event.key == pygame.K_a:
                    angle += Pi/24
                    angle = max(min(angle, Pi/8), -Pi/8)
                if event.key == pygame.K_d:
                    angle -= Pi/24
                    angle = max(min(angle, Pi/8), -Pi/8)
                if event.key == pygame.K_u:
                    velocity += Pi/16
                if event.key == pygame.K_i:
                    velocity -= Pi/16
        if joystick != None:
            if mode == "MANUAL":
                if event.type == pygame.JOYAXISMOTION:
                    angle = joystick.get_axis(WHEELAX)*Pi/8
                    angle = max(min(angle, Pi/8), -Pi/8)
                    velocity = 0
                    velocity += (joystick.get_axis(1)-1)*-1
                    velocity += joystick.get_axis(2)-1
                    velocity = max(min(velocity, 3), -3)
            if event.type==pygame.JOYBUTTONDOWN:
                #if joystick.get_button(2):
                #    stop = True
                    
                if joystick.get_button(3):
                    mode = "MANUAL"
                    velocity = 0
                
                if joystick.get_button(4):
                    mode = "PARKING"
                    
                if joystick.get_button(5):
                    velocity = 2
                    mode = "AUTO"

    return stop, angle, velocity, mode

# ==========================================================
#                     SENSOR READING
# ==========================================================
def read_sensors(sim, car, front_sensor):
    detected_front, dist_front, obst_pos, *_ = sim.readProximitySensor(front_sensor)
    car_pos = sim.getObjectPosition(car, -1)
    car_ori = sim.getObjectOrientation(car, -1)

    return detected_front, obst_pos, car_pos, car_ori


# ==========================================================
#             REFERENCE & PARKING LOGIC
# ==========================================================
def update_reference(sim, ref_points, ref_index, car_pos, ref_pos,
                     lets_start_parking, park_1, park_2, mode):

    x_car, y_car, _ = car_pos
    x_ref, y_ref, _ = ref_pos

    # go to next reference
    if ((x_car - x_ref)**2 + (y_car - y_ref)**2 < 0.3) and not lets_start_parking:
        sim.setShapeColor(ref_points[ref_index], None, sim.colorcomponent_ambient_diffuse, [1, 0, 0])
        ref_index += 1
        if ref_index >= len(ref_points):
            ref_index = 0
        sim.setShapeColor(ref_points[ref_index], None, sim.colorcomponent_ambient_diffuse, [0, 1, 0])
        ref_pos = sim.getObjectPosition(ref_points[ref_index])
        

    # initiate parking
    park2_pos = sim.getObjectPosition(park_2)

    if mode == "PARKING" and x_car < park2_pos[0] and y_car > park2_pos[1] and not lets_start_parking:
        lets_start_parking = True
        ref_pos = sim.getObjectPosition(park_1)
        print("parking initiated")

    return ref_pos, ref_index, lets_start_parking


# ==========================================================
#             OBSTACLE AVOIDANCE STEERING
# ==========================================================
def avoid_obstacles(obst_pos):
    target_angle = math.atan2(obst_pos[2], obst_pos[0])
    if target_angle - Pi/2 < 0:
        return Pi/8
    else:
        return -Pi/8


# ==========================================================
#                     PID HEADING CONTROL
# ==========================================================
def pid_control(car_pos, car_ori, ref_pos, pid_data):
    Kp_ref, Ki_ref, Kd_ref, pid_integral, pid_prev_error, dt = pid_data

    x_ref, y_ref, _ = ref_pos
    x_car, y_car, _ = car_pos

    target_angle = math.atan2(y_ref - y_car, x_ref - x_car)
    car_yaw = car_ori[2]

    # heading error
    error = (car_yaw - target_angle + math.pi) % (2 * math.pi) - math.pi

    pid_integral += error * dt
    derivative = (error - pid_prev_error) / dt

    steer = Kp_ref * error + Kd_ref * derivative
    steer = max(min(steer, Pi/8), -Pi/8)

    return steer, (pid_integral, error)


# ==========================================================
#                     APPLY STEERING & DRIVE
# ==========================================================
def apply_controls(sim, car_left_axel, car_right_axel, carLeftMotor, carRightMotor,
                   angle, velocity):
    sim.setObjectOrientation(car_right_axel, [-Pi/2, angle, 0], sim.getObject('/Car'))
    sim.setObjectOrientation(car_left_axel, [-Pi/2, angle, 0], sim.getObject('/Car'))

    sim.setJointTargetVelocity(carLeftMotor, velocity)
    sim.setJointTargetVelocity(carRightMotor, velocity)

def draw_tui(angle, velocity, mode):
    """
    Draws a simple text-based dashboard in the terminal.
    """
    print("\033[2J\033[H", end="")  # clear terminal
    print("=======================================")
    print("              CAR STATUS               ")
    print("=======================================\n")
    print(f" Mode:     {mode}")
    print(f" Speed:    {velocity:.2f}")
    print(f" Steering: {math.degrees(angle):.1f}°")
    print("\n(Press Q to exit, P to park)")
    print("=======================================")


# ==========================================================
#                        MAIN LOOP
# ==========================================================
def main_loop():

    sim, car, carLeftMotor, carRightMotor, car_left_axel, car_right_axel, \
    front_sensor, ref_points, park_1, park_2, mode = init_sim()

    sim.startSimulation()

    print('# JS= ',pygame.joystick.get_count())
    if (pygame.joystick.get_count()>0):
        sleep(2)
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(joystick.get_guid())
        print(joystick.get_name())
        numAx=joystick.get_numaxes()
        print(numAx)
        print(joystick.get_numballs())
        print(joystick.get_numhats())
        numBt=joystick.get_numbuttons()
        print(numBt)
    else:
        joystick = None
        print("Joystick not detected!")
        sleep(5)
    
    angle = 0
    velocity = 0
    lets_start_parking = False

    ref_index = 0
    ref_pos = sim.getObjectPosition(ref_points[ref_index])

    # PID parameters
    Kp_ref, Ki_ref, Kd_ref = 1.5, 0.05, 0.3
    pid_integral = 0.0
    pid_prev_error = 0.0
    dt = 0.05

    stop = False
    while not stop:

        # ------------------------
        #  USER INPUT
        # ------------------------
        stop, angle, velocity, new_mode = read_inputs(angle, velocity, mode, stop, joystick)
        if new_mode != mode and new_mode == "MANUAL":
            for ref in ref_points:
                sim.setShapeColor(ref, None, sim.colorcomponent_ambient_diffuse, [1, 0, 0])

        """
        if new_mode != mode and new_mode == "AUTO":
            sim.setShapeColor(ref_points[ref_index], None, sim.colorcomponent_ambient_diffuse, [1, 0, 0])
            car_pos = sim.getObjectPosition(car)
            x_car, y_car, _ = car_pos
            min_dist = 100000

            # find min distance to a ref
            for index, loop_ref_pos in enumerate(ref_points):
                x_ref, y_ref, _ = sim.getObjectPosition(loop_ref_pos)
                if (x_car - x_ref)**2 + (y_car - y_ref)**2 < min_dist:
                    ref_pos = sim.getObjectPosition(loop_ref_pos)
                    ref_index = index
                    min_dist = (x_car - x_ref)**2 + (y_car - y_ref)**2
            sim.setShapeColor(ref_points[ref_index], None, sim.colorcomponent_ambient_diffuse, [0, 1, 0])"""

        if new_mode != mode and new_mode == "AUTO":
            # Color current point red
            sim.setShapeColor(ref_points[ref_index], None, sim.colorcomponent_ambient_diffuse, [1, 0, 0])

            # Get car angle around origin
            car_x, car_y, _ = sim.getObjectPosition(car)
            car_angle = math.atan2(car_y, car_x)

            next_index = None
            smallest_delta = 0

            for index, ref in enumerate(ref_points):
                x_ref, y_ref, _ = sim.getObjectPosition(ref)
                ref_angle = math.atan2(x_ref, y_ref)

                # Correct: use atan2(y, x)
                # ref_angle = math.atan2(y_ref, x_ref)

                # Compute angle difference in range [0, 2π)
                delta = (ref_angle - car_angle) % (2 * math.pi)

                # We want the *next* point → smallest positive delta
                if delta > smallest_delta:
                    smallest_delta = delta
                    next_index = index

            # Fallback: if no point found, go to 0
            if next_index is None:
                next_index = 0

            # Set next point
            ref_index = next_index

            # Color next point green
            sim.setShapeColor(ref_points[ref_index], None, sim.colorcomponent_ambient_diffuse, [0, 1, 0])

        mode = new_mode

			
        # ------------------------
        #  SENSORS
        # ------------------------
        
        detected, obst_pos, car_pos, car_ori = read_sensors(sim, car, front_sensor)

        # ------------------------
        #  UPDATE REFERENCES
        # ------------------------
        ref_pos, ref_index, lets_start_parking = update_reference(sim, ref_points, ref_index, car_pos, ref_pos, lets_start_parking, park_1, park_2, mode)

        # ------------------------
        #  OBSTACLE AVOIDANCE
        # ------------------------
        if mode != "MANUAL":
            if detected:
                angle = avoid_obstacles(obst_pos)

            else:
                # PID pose tracking
                pid_data = (Kp_ref, Ki_ref, Kd_ref, pid_integral, pid_prev_error, dt)
                angle, (pid_integral, pid_prev_error) = pid_control(
                    car_pos, car_ori, ref_pos, pid_data
                )

        # ------------------------
        #  PARKING LOGIC
        # ------------------------
        if mode == "PARKING":
            x_car, y_car, _ = car_pos
            x_ref, y_ref, _ = ref_pos

            if ((x_car-x_ref)**2 + (y_car-y_ref)**2 < 0.3) and lets_start_parking:
                if ref_pos == sim.getObjectPosition(park_2):
                    velocity = 0
                    angle = 0
                else:
                    ref_pos = sim.getObjectPosition(park_2)
                    velocity = -2

        # ------------------------
        #  APPLY TO MOTORS
        # ------------------------
        apply_controls(sim, car_left_axel, car_right_axel,
                       carLeftMotor, carRightMotor, angle, velocity)

        # ------------------------
        #  DRAW TUI
        # ------------------------
        draw_tui(angle, velocity, mode)

        sim.step()

    sim.stopSimulation()


# ==========================================================
#                   PROGRAM ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    init_pygame()
    main_loop()

