# -*- coding: utf-8 -*-
import sys, time, cv2, imgui, threading, pygame
import OpenGL.GL as gl
from djitellopy import Tello
from imgui.integrations.pygame import PygameRenderer
from imgui_datascience import imgui_cv


# TODO: installs: git+https://github.com/pyimgui/pyimgui.git@dev/version-2.0 djitellopy imgui_datascience

popups = []

config = {
    "dont_reconnect": False,
    "cam_on": False,
    "speed": 50,
    "rotation_speed": 50
}

keys = {
    "w": False,
    "a": False,
    "s": False,
    "d": False,
    "left_arrow": False,
    "right_arrow": False,
    "up_arrow": False,
    "down_arrow": False
}


def main():
    global keys

    pygame.init()
    size = 1280, 720

    pygame.display.set_mode(size, pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)
    pygame.display.set_caption("Drone GUI")

    imgui.create_context()
    impl = PygameRenderer()

    io = imgui.get_io()
    io.display_size = size
    io.config_windows_move_from_title_bar_only = True

    tello = Tello()
    threading.Thread(target=tello.send_command_with_return, args=("command", 5)).start()  # wait_for_state == False!
    connect_time = time.time()
    frame_read = None
    battery = -1
    battery_time = time.time() - 10

    redraw = False
    redraw_time = time.time()

    while 1:
        redraw = False

        if tello.get_current_state() or connect_time + 5 > time.time() or 0 in popups or config["dont_reconnect"]:  #als hij na 5 seconden niet is verbonden, toon popup
            pass
        else:
            popups.append(0)
            redraw = True

        if tello.get_current_state() and battery_time + 10 < time.time():  #refresh elke 5 seconden de battery variabele
            battery_time = time.time()
            battery = tello.get_battery()
            redraw = True

        # keys = dict.fromkeys(keys, False)  # zet alles naar False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            redraw = True
            impl.process_event(event)

            if tello.get_current_state() is False:
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    tello.takeoff()
                if event.key == pygame.K_r: #TODO: thread deze 2 functies!
                    tello.land()
                if event.key == pygame.K_w:
                    keys["w"] = True
                if event.key == pygame.K_a:
                    keys["a"] = True
                if event.key == pygame.K_s:
                    keys["s"] = True
                if event.key == pygame.K_d:
                    keys["d"] = True
                if event.key == pygame.K_LEFT:
                    keys["left_arrow"] = True
                if event.key == pygame.K_RIGHT:
                    keys["right_arrow"] = True
                if event.key == pygame.K_UP:
                    keys["up_arrow"] = True
                if event.key == pygame.K_DOWN:
                    keys["down_arrow"] = True

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_w:
                    keys["w"] = False
                if event.key == pygame.K_a:
                    keys["a"] = False
                if event.key == pygame.K_s:
                    keys["s"] = False
                if event.key == pygame.K_d:
                    keys["d"] = False
                if event.key == pygame.K_LEFT:
                    keys["left_arrow"] = False
                if event.key == pygame.K_RIGHT:
                    keys["right_arrow"] = False
                if event.key == pygame.K_UP:
                    keys["up_arrow"] = False
                if event.key == pygame.K_DOWN:
                    keys["down_arrow"] = False

        if tello.get_current_state() or True:  #besturing
            speed = [0, 0, 0, 0]
            if keys["a"] is True and keys["d"] is False:
                # ga naar links
                speed[0] = -config["speed"]
            if keys["a"] is False and keys["d"] is True:
                # ga naar links
                speed[0] = config["speed"]
            if keys["w"] is True and keys["s"] is False:
                # ga vooruit
                speed[1] = config["speed"]
            if keys["w"] is False and keys["s"] is True:
                # ga achteruit
                speed[1] = -config["speed"]
            if keys["up_arrow"] is True and keys["down_arrow"] is False:
                speed[2] = config["speed"]
            if keys["up_arrow"] is False and keys["down_arrow"] is True:
                speed[2] = -config["speed"]
            if keys["left_arrow"] is True and keys["right_arrow"] is False:
                speed[3] = -config["rotation_speed"]
            if keys["left_arrow"] is False and keys["right_arrow"] is True:
                speed[3] = config["rotation_speed"]

            if speed[0] != 0 or speed[1] != 0 or speed[2] != 0 or speed[3] != 0:
                tello.send_rc_control(speed[0], speed[1], speed[2], speed[3])


        if redraw_time + 0.5 > time.time() and redraw is False:  #als het niet nodig is om nog een keer te renderen, doe het dan niet.
            time.sleep(0.01)
            continue

        redraw_time = time.time()

        imgui.new_frame()

        """if imgui.begin_main_menu_bar():
            if imgui.begin_menu("File", True):

                clicked_quit, selected_quit = imgui.menu_item(
                    "Quit", 'Cmd+Q', False, True
                )

                if clicked_quit:
                    exit(1)

                imgui.end_menu()
            imgui.end_main_menu_bar()"""


        if 0 in popups:
            # popup code 0
            x = pygame.display.get_window_size()[0] / 2
            y = popups.index(0) * 100
            imgui.set_next_window_position(x, y, imgui.ALWAYS, 0.5, 0) #  set window position, 0.5 = center x-axis
            imgui.calculate_item_width()
            imgui.begin("Melding 0!")
            imgui.text("Kon niet verbinden met de drone.")
            if imgui.button("Opnieuw verbinden"):
                threading.Thread(target=tello.send_command_with_return, args=("command", 5)).start()  # wait_for_state == False!
                connect_time = time.time()
                popups.remove(0)

            if imgui.button("Niet opnieuw verbinden"):
                config["dont_reconnect"] = True
                popups.remove(0)

            imgui.end()

        if 69 in popups:
            # test popup
            x = pygame.display.get_window_size()[0] / 2
            y = popups.index(69) * 100
            imgui.set_next_window_position(x, y, imgui.ALWAYS, 0.5, 0) #  set window position, 0.5 = center x-axis
            imgui.calculate_item_width()
            imgui.begin("Melding 69!", True)
            imgui.text("TEST!")
            imgui.text(" ")
            if imgui.button("close"):
                popups.remove(69)

            imgui.end()

        imgui.begin("Controls")

        """
        import cv2
        import urllib.request
        import numpy as np
        url = "https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fwallup.net%2Fwp-content%2Fuploads%2F2016%2F03%2F10%2F343179-landscape-nature.jpg"
        url_response = urllib.request.urlopen(url)
        img = cv2.imdecode(np.array(bytearray(url_response.read()), dtype=np.uint8), -1)
        ^^ zet dit in tello.py ipv "cv2.VideoCapture(address)"
        """

        if config["cam_on"]:
            if tello.get_current_state():
                if frame_read is not None:  # voor de zekerheid kijken of dit al een waarde heeft
                    imgui_cv.image(frame_read.frame, 720, 480)
                    # imgui_cv.image(cv2.imread("neonoir.jpg"), 720, 480)

        if imgui.button("Toggle de camera"):
            if config["cam_on"]:
                tello.streamoff()
                config["cam_on"] = False
            tello.streamon()
            # frame_read = tello.get_frame_read()
            config["cam_on"] = True

        if imgui.button("test popup"):
            if 69 not in popups:
                popups.append(69)

        config["speed"] = imgui.slider_int("Vlieg snelheid", config["speed"], 0, 100)[1]
        config["rotation_speed"] = imgui.slider_int("Draai snelheid", config["rotation_speed"], 0, 100)[1]
        imgui.text("De batterij is " + str(battery) + "%")

        imgui.text(" ")

        imgui.text("Besturing:")
        imgui.text("E: Opstijgen")
        imgui.text("R: Landen")
        imgui.text("WASD: Vliegen")
        imgui.text("Pijltjestoetsen links en rechts: draaien")
        imgui.text("Pijltjestoetsen omhoog/beneden: omhoog / naar beneden")

        imgui.end()

        gl.glClearColor(0.4, 0.4, 0.4, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        imgui.render()
        impl.render(imgui.get_draw_data())
        pygame.display.flip()


if __name__ == "__main__":
    main()
