import pygame
from time import sleep

HOMEBT=0
WHEELAX=0
SPEEDAXIS=1

pygame.init()
screen = pygame.display.set_mode((128, 72))
stop=False

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


pygame.event.get()
while not stop:
    events = pygame.event.get()
    for event in events:
        print('TYPE: ',pygame.event.event_name(event.type))
        if event.type==pygame.KEYDOWN:
            print('KEY: ',event.key)
            if event.key==pygame.K_a:
                print('CHAR: A')
            if event.key==pygame.K_l:
                print('CHAR: L')
            if event.key==pygame.K_q:
               stop=True
        elif event.type==pygame.JOYBUTTONDOWN:
            print('---BT---')
            for n in range(numBt):
                print(n,' : ',joystick.get_button(n))
            print('--------')
            if joystick.get_button(HOMEBT):
               stop=True
        elif event.type==pygame.JOYAXISMOTION:
            print('---AX---')
            for n in range(numAx):
                print(n,' : ',-1*(joystick.get_axis(n)-1))
            print(' : ',joystick.get_axis(WHEELAX))
            print('--------')
            
joystick.quit()
pygame.quit()

