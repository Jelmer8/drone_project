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


def main():

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
    threading.Thread(target=tello.send_command_with_return, args=("command",5)).start()  # wait_for_state == False!
    connect_time = time.time()
    frame_read = None

    while 1:

        if tello.get_current_state() or connect_time + 5 > time.time() or 0 in popups or config["dont_reconnect"]:
            pass
        else:
            popups.append(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            impl.process_event(event)

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
            x = size[0] / 2
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
            x = size[0] / 2
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
                if frame_read != None:  # voor de zekerheid kijken of dit al een waarde heeft
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

        imgui.end()

        gl.glClearColor(0.4, 0.4, 0.4, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        imgui.render()
        impl.render(imgui.get_draw_data())
        pygame.display.flip()

if __name__ == "__main__":
    main()
