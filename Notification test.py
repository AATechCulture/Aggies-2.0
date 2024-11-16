import tkinter as tk


def show_notification(message):
    # Create the main window
    root = tk.Tk()
    root.title("Notification")

    # Set window size and position
    root.geometry("300x100+100+100")
    root.resizable(False, False)

    # Create and configure the label for the message
    label = tk.Label(root, text=message, font=("Arial", 12), wraplength=280, justify="center")
    label.pack(expand=True)

    # Schedule the window to close after 15 seconds
    root.after(3500, root.destroy)

    # Run the Tkinter event loop
    root.mainloop()


# Example usage
show_notification("This is a notification message. It will disappear in 15 seconds.")
