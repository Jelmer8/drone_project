from concurrent.futures import thread
import sys, time, imgui, threading, pygame, cv2
import OpenGL.GL as gl
from djitellopy import Tello
from imgui.integrations.pygame import PygameRenderer
from imgui_datascience import imgui_cv
#import numpy as np
import handtracking as htm
#from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
#from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


# TODO: installs: git+https://github.com/pyimgui/pyimgui.git@dev/version-2.0 djitellopy imgui_datascience

popups = []#hier komen popup-indices in

imageAdjustments = imgui_cv.ImageAdjustments()#er moet altijd dezelfde wijziging aangebracht worden op de camera (niks.)
texture_id = 0#OpenGL texture id voor de camera
new_texture_id = None
handControlSpeed = 0
handControlRotation = 0
handControlSpeedUD = 0
pTime = 0
detector = htm.handDetector(detectionCon=0.7, maxHands=10)
actions = None

config = {#instelbare variabelen
    "dont_reconnect": False,
    "cam_on": False,
    "speed": 50,
    "rotation_speed": 50,
    "follow_speed": 40,
    "cam_res": [720, 480],
    "track_hand": False
}

speedIndex = 0
speeds = [(50, 50), (50, 100), (100, 100)]

keys = {#toetsen die je indrukt
    "w": False,
    "a": False,
    "s": False,
    "d": False,
    "left_arrow": False,
    "right_arrow": False,
    "up_arrow": False,
    "down_arrow": False
}

tello = Tello()#maak een nieuwe tello instance

def main():
    global keys, tello, texture_id, new_texture_id, imageAdjustments, handControlSpeed, actions#global omdat we deze hierin willen gebruiken/aanpassen

    pygame.init()#maak een pygame window
    size = 1280, 720#met deze grootte

    pygame.display.set_mode(size, pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)#set een aantal modes
    pygame.display.set_caption("Drone GUI")#window titel

    imgui.create_context()#maak de opengl context van imgui
    impl = PygameRenderer()#we gaan pygame backend gebruiken met imgui

    io = imgui.get_io()
    io.display_size = size#set een aantal dingen in de context
    io.config_windows_move_from_title_bar_only = True

    threading.Thread(target=tello.send_command_with_return, args=("command", 5)).start()#probeer te verbinden
    threading.Thread(target=blockingActionsThread).start()#start de blockingActionsThread
    connect_time = time.time()#wanneer probeerde ik voor het laatst om te verbinden?
    frame_read = None#hier komt de frame_read in
    battery = -1#zet een tijdelijke waarde in de battery level variabele
    battery_time = time.time() - 10#dit is wanneer de battery level voor het laatst geupdate is

    redraw = False#is het nodig om de UI opnieuw te renderen?
    redraw_time = time.time()#we renderen in ieder geval elke x seconden, houd hier de tijd bij

    while 1:
        redraw = False#niet opnieuw renderen, tenzij ...

        if tello.get_current_state() or connect_time + 5 > time.time() or 0 in popups or config["dont_reconnect"]:  #als hij na 5 seconden niet is verbonden, toon popup
            pass#als hij al verbonden is of er nog even gewacht moet worden voordat we het opnieuw proberen
        else:
            popups.append(0)#geef de optie om opnieuw te verbinden
            redraw = True#sowieso opnieuw renderen ivm nieuwe popup

        if tello.get_current_state() and battery_time + 10 < time.time():  #refresh elke 10 seconden de battery variabele
            battery_time = time.time()#laatste update
            battery = tello.get_battery()#update de battery level
            redraw = True#sowieso opnieuw renderen ivm veranderde tekst
            #tello.set_video_resolution(tello.RESOLUTION_480P)

        for event in pygame.event.get():#loop door alle events die zijn gebeurd
            if event.type == pygame.QUIT:#als er afgesloten moet worden
                sys.exit()#exit het script

            redraw = True#we moeten opnieuw renderen, er is een event geweest
            impl.process_event(event)#process de events in imgui

            if tello.get_current_state() is False:#als hij niet verbonden is, ga naar volgende event
                continue
            if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                process_event(event.type, event.key)#process de events

        drone_movement()#beweeg de drone als er toetsen ingedrukt zijn


        if redraw_time + 0.5 > time.time() and redraw is False and config["cam_on"] is False:  #als het niet nodig is om nog een keer te renderen, doe het dan niet.
            time.sleep(0.01)#even wachten voordat we opnieuw deze loop doen
            continue

        redraw_time = time.time()#ik ga alles opnieuw renderen

        imgui.new_frame()#begin een nieuwe frame

        """if imgui.begin_main_menu_bar():
            if imgui.begin_menu("File", True):

                clicked_quit, selected_quit = imgui.menu_item(
                    "Quit", 'Cmd+Q', False, True
                )

                if clicked_quit:
                    exit(1)

                imgui.end_menu()
            imgui.end_main_menu_bar()"""


        if 0 in popups:#als popup 0 getoond moet worden
            # popup code 0
            x = pygame.display.get_window_size()[0] / 2#positie van de popup
            y = popups.index(0) * 100
            imgui.set_next_window_position(x, y, imgui.ALWAYS, 0.5, 0)#set window position, 0.5 = center x-axis
            imgui.begin("Melding 0!")#begin een nieuwe window in imgui
            imgui.text("Kon niet verbinden met de drone.")#wat tekst erin
            if imgui.button("Opnieuw verbinden"):#als er op de knop gedrukt word
                popups.remove(0)#haal de popup weer weg
                threading.Thread(target=tello.send_command_with_return, args=("command", 5)).start()#probeer weer te verbinden
                connect_time = time.time()#ik probeer nu te verbinden

            if imgui.button("Niet opnieuw verbinden"):#als er op deze knop gedrukt word
                config["dont_reconnect"] = True#niet weer opnieuw verbinden. handig voor testen
                popups.remove(0)

            imgui.end()#einde van de window in imgui

        if 69 in popups:#weer hetzelfde doen TODO: misschien een ander systeem hiervoor maken?
            # test popup
            x = pygame.display.get_window_size()[0] / 2
            y = popups.index(69) * 100
            imgui.set_next_window_position(x, y, imgui.ALWAYS, 0.5, 0) #  set window position, 0.5 = center x-axis
            imgui.begin("Melding 69!", True)
            imgui.text("TEST!")
            imgui.text(" ")
            if imgui.button("close"):
                popups.remove(69)

            imgui.end()

        imgui.begin("Controls")#begin de controls window

        if imgui.button("Toggle de camera"):#als je op de knop drukt
            if config["cam_on"]:# zet de camera aan of uit
                if actions == None:
                    actions = "streamoff"
                
            else:
                if actions == None:
                    actions = "streamon"
                    if frame_read is None:
                        frame_read = tello.get_frame_read()#als de variabele nog niet gedefinieerd was, doe het nu

        track_hand_txt = ""

        if config["track_hand"]:
            track_hand_txt = "uit."
        else:
            track_hand_txt = "aan."


        if imgui.button("Zet hand-tracking " + track_hand_txt):
            if config["track_hand"]:
                config["track_hand"] = False
                handControlSpeed = 0
            else:
                actions = "streamon"
                if frame_read is None:
                    frame_read = tello.get_frame_read()
                config["track_hand"] = True

        if imgui.button("test popup"):#handig voor testen
            if 69 not in popups:
                popups.append(69)

        config["speed"] = imgui.slider_int("Vlieg snelheid", config["speed"], 0, 100)[1]
        config["rotation_speed"] = imgui.slider_int("Draai snelheid", config["rotation_speed"], 0, 100)[1]#een aantal sliders maken voor de snelheid
        imgui.text("De batterij is " + str(battery) + "%")#battery %

        config["follow_speed"] = imgui.slider_int("Volg snelheid", config["follow_speed"], 0, 100)[1]
        

        imgui.text(" ")#geef heel wat tekst weer

        imgui.text("Besturing:")
        imgui.text("E: opstijgen")
        imgui.text("R: landen")
        imgui.text("1,2,3,4: flips")
        imgui.text("W/S: omhoog/omlaag")
        imgui.text("Pijltjestoetsen links en rechts: draaien")
        imgui.text("Pijltjestoetsen omhoog/beneden: naar voor/achter")

        imgui.end()#eindig huidige window

        if config["cam_on"]:
            if tello.get_current_state():#als hij verbonden is
                if frame_read is not None and frame_read.frame is not None:#als frame_read en frame_read.frame een waarde hebben
                    imgui.begin("Camera")
                    frame = frame_read.frame
                    if config["track_hand"]:
                        frame = trackHand(frame)
                    render_camera(frame)#sla de texture id op van de texture in de gpu memory zodat we deze er later weer uit kunnen halen
                    imgui.end()

        gl.glClearColor(0.4, 0.4, 0.4, 1)#clear de pygame window
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        imgui.render()#render de imgui UI
        impl.render(imgui.get_draw_data())#plaats het gerenderde plaatje op de pygame window

        pygame.display.flip()#flip de buffer (laat het nieuwe beeld zien)

        if new_texture_id != texture_id:
            gl.glDeleteTextures(1, [texture_id])#vorige texture opruimen (pas na het flippen van de display)
        if new_texture_id != None:#als new_texture_id een waarde heeft, zet deze in texture_id
            texture_id = new_texture_id


def render_camera(frame):#render het camera beeld
    global new_texture_id
    imageAndAdjustments = imgui_cv.ImageAndAdjustments(frame, imageAdjustments)
    new_texture_id = imgui_cv._image_to_texture(imageAndAdjustments)
    title = "hoogte: " + str(tello.get_height() + 20)
    viewport_size = imgui_cv._image_viewport_size(imageAndAdjustments.image, config["cam_res"][0], config["cam_res"][1])
    if title == "":
        imgui.image_button(new_texture_id, viewport_size.width, viewport_size.height, frame_padding=0)
    else:
        imgui.begin_group()
        imgui.image_button(new_texture_id, viewport_size.width, viewport_size.height, frame_padding=0)
        imgui.text(title)
        imgui.end_group()


def process_event(type, key):
    global keys, tello, actions, speedIndex, speeds

    if type == pygame.KEYDOWN:
        if key == pygame.K_e and not tello.is_flying:
            if actions is None:
                actions = "takeoff"
        if key == pygame.K_q and tello.is_flying:
            if actions is None:
                actions = "land"
        if key == pygame.K_1 or key == pygame.K_KP8:
            if actions is None:
                actions = "flip_forward"
        if key == pygame.K_2 or key == pygame.K_KP6:
            if actions is None:
                actions = "flip_right"
        if key == pygame.K_3 or key == pygame.K_KP2:
            if actions is None:
                actions = "flip_back"
        if key == pygame.K_4 or key == pygame.K_KP4:
            if actions is None:
                actions = "flip_left"
        if key == pygame.K_w:
            keys["w"] = True
        if key == pygame.K_a:
            keys["a"] = True
        if key == pygame.K_s:
            keys["s"] = True
        if key == pygame.K_d:
            keys["d"] = True
        if key == pygame.K_LEFT:
            keys["left_arrow"] = True
        if key == pygame.K_RIGHT:
            keys["right_arrow"] = True
        if key == pygame.K_UP:
            keys["up_arrow"] = True
        if key == pygame.K_DOWN:
            keys["down_arrow"] = True
        if key == pygame.K_z:
            speedIndex += 1
            if speedIndex == len(speeds):
                speedIndex = 0
            
            config["speed"] = speeds[speedIndex][0]
            config["rotation_speed"] = speeds[speedIndex][1]

    if type == pygame.KEYUP:
        if key == pygame.K_w:
            keys["w"] = False
        if key == pygame.K_a:
            keys["a"] = False
        if key == pygame.K_s:
            keys["s"] = False
        if key == pygame.K_d:
            keys["d"] = False
        if key == pygame.K_LEFT:
            keys["left_arrow"] = False
        if key == pygame.K_RIGHT:
            keys["right_arrow"] = False
        if key == pygame.K_UP:
            keys["up_arrow"] = False
        if key == pygame.K_DOWN:
            keys["down_arrow"] = False


def drone_movement():
    if tello.get_current_state() and tello.is_flying:#als de tello verbonden is, doe de besturing

        if handControlSpeed != 0 or handControlRotation != 0 or handControlSpeedUD != 0:
            tello.send_rc_control(0, round(-config["follow_speed"] * handControlSpeed), round(-40 * handControlSpeedUD), round(50 * handControlRotation))
            return
        

        speed = [0, 0, 0, 0]
        if keys["left_arrow"] is True and keys["right_arrow"] is False:
            # ga naar links
            speed[0] = -config["speed"]
        if keys["left_arrow"] is False and keys["right_arrow"] is True:
            # ga naar links
            speed[0] = config["speed"]
        if keys["up_arrow"] is True and keys["down_arrow"] is False:
            # ga vooruit
            speed[1] = config["speed"]
        if keys["up_arrow"] is False and keys["down_arrow"] is True:
            # ga achteruit
            speed[1] = -config["speed"]
        if keys["w"] is True and keys["s"] is False:
            speed[2] = config["speed"]
        if keys["w"] is False and keys["s"] is True:
            speed[2] = -config["speed"]
        if keys["a"] is True and keys["d"] is False:
            speed[3] = -config["rotation_speed"]
        if keys["a"] is False and keys["d"] is True:
            speed[3] = config["rotation_speed"]

        tello.send_rc_control(speed[0], speed[1], speed[2], speed[3])



highest = 0
def filterLmList(val):
    if val[2] == highest:
        return True
    else:
        return False



def trackHand(img):
    global pTime, detector, handControlSpeed, handControlRotation, handControlSpeedUD, actions, highest

    if actions is not None:
        handControlRotation = 0
        handControlSpeed = 0
        handControlSpeedUD = 0
        return img

    # Find Hand
    img = detector.findHands(img)
    lmList, bbox = detector.findPosition(img, draw=True)
    fingers = None

    if len(lmList) != 0:
        fingers = detector.fingersUp()
        highest = 0
        for v in lmList:#TODO: werkt dit?
            if v[2] > highest:
                highest = v[2]
        lmList = list(map(filterLmList, lmList))
        print(len(lmList))

    if len(lmList) != 0 and tello.is_flying is False:
        if fingers[1] and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0:
            if actions is None:
                actions = "takeoff"
                return img


    if len(lmList) != 0 and tello.is_flying:#als er meer dan 0 handen zijn

        h, w, c = img.shape

        #img = cv2.putText(img, str(lmList[0][1]) + "," + str(w), (100, 100), cv2.FONT_HERSHEY_COMPLEX, 2, (255, 255, 255))

        
        if fingers[0] and fingers[1] and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0:
            if actions is None:
                actions = "land"
                return img

        if fingers[1] == 0 and fingers[2] and fingers[3] == 0 and fingers[4] == 0:
            if actions is None:
                actions = "flip_back"
                return img

        
            

        xMid = lmList[0][1]
        yMid = lmList[0][2]

        #print(xMid)

        if xMid > w - 350:
            handControlRotation = 1
        elif xMid < 350:
            handControlRotation = -1
        else:
            handControlRotation = 0

        if yMid > h - 200:
            handControlSpeedUD = 1
        elif yMid < 200:
            handControlSpeedUD = -1
        else:
            handControlSpeedUD = 0



        #bbox = xmin, ymin, xmax, ymax
 
        # Filter based on size
        #area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) // 100
        # print(area)

        length, img, lineInfo = detector.findDistance(0, 9, img)#vind afstand tussen de punten 0 en 9

        #230 length == goede afstand ; gedeeld door 2 omdat we nu punt 9 gebruiken
        if length > 120 + 50:
            #te dichtbij
            handControlSpeed = 1
        elif length < 120 - 50:
            #te ver weg
            handControlSpeed = -1
        else:
            if handControlSpeed == 1:#een beetje tegensturen zodat hij (hopelijk) meteen stilstaat
                #print("tegensturen1")
                handControlSpeed = -0.9
            elif handControlSpeed == -1:
                #print("tegensturen2")
                handControlSpeed = 0.9
            else:#niet terugsturen als we al stilstonden
                if handControlSpeed > -0.01 and handControlSpeed < 0.01:
                    handControlSpeed = 0
                    
                else:
                    #print("tegensturen3: " + str(handControlSpeed))
                    if handControlSpeed < 0:
                        handControlSpeed += 0.1
                    else:
                        handControlSpeed -= 0.1
                    
    else:
        if (handControlSpeed > -0.01 and handControlSpeed < 0.01) is False and handControlSpeed != 1 and handControlSpeed != -1:
            if handControlSpeed < 0:
                handControlSpeed += 0.075
            else:
                handControlSpeed -= 0.075
        else:
            handControlSpeed = 0
        handControlRotation = 0
        handControlSpeedUD = 0
 
    # Frame rate
    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime
    cv2.putText(img, f'FPS: {int(fps)}', (40, 50), cv2.FONT_HERSHEY_COMPLEX,
                1, (255, 0, 0), 3)

    return img


def blockingActionsThread():#thread zodat niet alles vastloopt als je een van deze dingen doet
    global actions
    while True:
        if actions is not None and tello.get_current_state():
            if actions == "takeoff":
                tello.takeoff()
            elif actions == "land":
                tello.land()
            elif actions == "flip_right":
                tello.flip_right()
            elif actions == "flip_left":
                tello.flip_left()
            elif actions == "flip_back":
                tello.flip_back()
            elif actions == "flip_forward":
                tello.flip_forward()
            elif actions == "streamoff":
                tello.streamoff()
                config["cam_on"] = False
            elif actions == "streamon":
                tello.streamon()
                config["cam_on"] = True

            actions = None


        time.sleep(0.25)

if __name__ == "__main__":
    main()
