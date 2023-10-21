import pyautogui
import pydirectinput
import time

print("You are going to get so many shinies king.")

emulator_x = 0 
emulator_y = 0 
emulator_width = 2560 
emulator_height = 1440 


pyautogui.PAUSE = 2
pydirectinput.PAUSE = 1

def restart(): 
    pydirectinput.keyDown('backspace')
    pydirectinput.keyDown('enter')
    pydirectinput.keyDown('x')
    pydirectinput.keyDown('z')
    pydirectinput.keyUp('backspace')
    pydirectinput.keyUp('enter')
    pydirectinput.keyUp('x')
    pydirectinput.keyUp('z')
    
    return True
    


def countdown(seconds): 
    while seconds > 0: 
        print("Starting in:",  seconds)
        time.sleep(1)
        seconds -= 1


def mewtwo(): 
    count = 0
    mewtwoPic = True 
    print('Initializing Mewto Hunt')

    # Player must start from in game right in front of mewtwo 
    countdown(5)

    while (mewtwoPic): 
        print("Attempt #", count)
        pydirectinput.press('x')
        pydirectinput.press('x')
        # Check if shiny
        time.sleep(5)

        shinyMewtwoPic = pyautogui.locateOnScreen('green.png')

        print("Mewtwo Pic", shinyMewtwoPic)

        screenshot = pyautogui.screenshot(region=(emulator_x, emulator_y, emulator_width, emulator_height))

        screenshot.save('emulator_screenshot.png')


        if (shinyMewtwoPic):
            print("SHINY FOUND")
            screenshot = pyautogui.screenshot(region=(emulator_x, emulator_y, emulator_width, emulator_height))

            screenshot.save('shiny_screenshot.png')
            exit()


        # if not shiny restart game 
        restart()
        count += 1
        pydirectinput.press('x')
        pydirectinput.press('x')
        pydirectinput.press('x')
        pydirectinput.press('x')
        pydirectinput.press('z')





if __name__ == '__main__': 
    mewtwo()

