# **Shiny Hunter**

A Python-based project utilizing tools such as Tkinter and PyAutoGUI that allows the user to embed a running Pokemon game window into the application that then inputs a series of keystroke combinations to automatically encounter desired Pokemon and reset via until it runs into a shiny version of said Pokemon. (See: Shiny Hunting to learn more about shiny hunting) The keystrokes are directly input into the window so the application is able to run minimized and/or in the background to allow use of the computer while the task is completed.

Currently, as a proof of concept, the application is built only to look for shiny mewtwo colors.

### Tools used: 
	- Python
	- Tkinter 
	- PyAutoGUI 
	- PyWin32

### How it Works: 
	Disclaimer - The user needs to provide the game application/emulator. 
	1.  Launch the game application
	2.  Launch the Shiny Hunter application 
	3.  Select the game application window from the drop-down menu and select "Launch Application."
	4.  Start hunting (assuming the player is in front of the static encounter)
	


### Instructions to Run: 
	- Install requirements (TBD) 
	- Run the main file 

### Features: 
	- Embed game application into shiny hunter application 
	- Direct input into the game window 
	- Image Detection 

### Planned Features: 
	- Customizable Input Buttons 
	- Add support for custom hunts 
		○ User target color 
		○ User input target sequence
