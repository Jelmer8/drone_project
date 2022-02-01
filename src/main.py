import sys, time, imgui, threading, pygame
import OpenGL.GL as gl
from djitellopy import Tello
from imgui.integrations.pygame import PygameRenderer
from imgui_datascience import imgui_cv


# TODO: installs: git+https://github.com/pyimgui/pyimgui.git@dev/version-2.0 djitellopy imgui_datascience

popups = []

imageAdjustments = imgui_cv.ImageAdjustments()
texture_id = 0#OpenGL texture id voor de camera

config = {
    "dont_reconnect": False,
    "cam_on": False,
    "speed": 50,
    "rotation_speed": 50,
    "cam_res": [360, 240]
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

tello = Tello()


def main():
    global keys, tello, texture_id, imageAdjustments

    pygame.init()
    size = 1280, 720

    pygame.display.set_mode(size, pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)
    pygame.display.set_caption("Drone GUI")

    imgui.create_context()
    impl = PygameRenderer()

    io = imgui.get_io()
    io.display_size = size
    io.config_windows_move_from_title_bar_only = True

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

        if tello.get_current_state() and battery_time + 10 < time.time():  #refresh elke 10 seconden de battery variabele
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
            if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                process_event(event.type, event.key)

        drone_movement()


        if redraw_time + 0.5 > time.time() and redraw is False and config["cam_on"] is False:  #als het niet nodig is om nog een keer te renderen, doe het dan niet.
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

        if imgui.button("Toggle de camera"):
            if config["cam_on"]:
                tello.streamoff()
                config["cam_on"] = False
            else: 
                tello.streamon()
                frame_read = tello.get_frame_read()
                config["cam_on"] = True

        if config["cam_on"]:
            if tello.get_current_state():
                if frame_read is not None:  # voor de zekerheid kijken of dit al een waarde heeft
                    frame = frame_read.frame
                    new_texture_id = render_camera(frame)
            

        if imgui.button("test popup"):
            if 69 not in popups:
                popups.append(69)

        config["speed"] = imgui.slider_int("Vlieg snelheid", config["speed"], 0, 100)[1]
        config["rotation_speed"] = imgui.slider_int("Draai snelheid", config["rotation_speed"], 0, 100)[1]
        imgui.text("De batterij is " + str(battery) + "%")
        

        imgui.text(" ")

        imgui.text("Besturing:")
        imgui.text("E: opstijgen")
        imgui.text("R: landen")
        imgui.text("1,2,3,4: flips")
        imgui.text("W/S: omhoog/omlaag")
        imgui.text("Pijltjestoetsen links en rechts: draaien")
        imgui.text("Pijltjestoetsen omhoog/beneden: naar voor/achter")

        imgui.end()

        gl.glClearColor(0.4, 0.4, 0.4, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        imgui.render()
        impl.render(imgui.get_draw_data())

        pygame.display.flip()

        #vorige texture opruimen (pas na het flippen van de display)
        gl.glDeleteTextures(1, [texture_id])
        if texture_id:
            texture_id = new_texture_id


def render_camera(frame):
    #imgui_cv.image(frame, 360, 240)
    imageAndAdjustments = imgui_cv.ImageAndAdjustments(frame, imageAdjustments)
    new_texture_id = imgui_cv._image_to_texture(imageAndAdjustments)
    title = ""
    viewport_size = imgui_cv._image_viewport_size(imageAndAdjustments.image, config["cam_res"][0], config["cam_res"][1])
    if title == "":
        imgui.image_button(new_texture_id, viewport_size.width, viewport_size.height, frame_padding=0)
    else:
        imgui.begin_group()
        imgui.image_button(new_texture_id, viewport_size.width, viewport_size.height, frame_padding=0)
        imgui.text(title)
        imgui.end_group()
    return new_texture_id


def process_event(type, key):
    global keys, tello

    if type == pygame.KEYDOWN:
        if key == pygame.K_e:
            tello.takeoff()
        if key == pygame.K_q: #TODO: thread deze 2 functies!
            tello.land()
        if key == pygame.K_1 or key == pygame.K_KP1:
            tello.flip_forward()
        if key == pygame.K_2 or key == pygame.K_KP2:
            tello.flip_right()
        if key == pygame.K_3 or key == pygame.K_KP3:
            tello.flip_back()
        if key == pygame.K_4 or key == pygame.K_KP4:
            tello.flip_left()
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
    if tello.get_current_state():  #besturing
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

if __name__ == "__main__":
    main()
