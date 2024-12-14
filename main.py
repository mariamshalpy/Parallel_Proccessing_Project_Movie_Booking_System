# %%
# At the top of the file, replace the existing user_windows list with:
user_windows = []  # To keep track of all user GUI instances



# %%
import sqlite3
def create_db():
    conn = sqlite3.connect('Movie_Ticket_Booking_System.db', check_same_thread=False)
    c = conn.cursor()
    
    # Table for movies with an active flag
    c.execute('''CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    hall TEXT,
                    time TEXT,
                    is_active BOOLEAN DEFAULT 1)''')

    # Table for seats
    c.execute('''CREATE TABLE IF NOT EXISTS seats (
                    id INTEGER PRIMARY KEY,
                    seat_number TEXT,
                    booked BOOLEAN,
                    user_name TEXT,
                    locked BOOLEAN,
                    movie_id INTEGER,
                    FOREIGN KEY (movie_id) REFERENCES movies (id))''')

    # Table for logs
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY,
                    action TEXT,
                    seat_number TEXT,
                    user_name TEXT,
                    movie_id INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()


# %%
def initialize_movies_and_seats():
    conn = sqlite3.connect('Movie_Ticket_Booking_System.db', check_same_thread=False)
    c = conn.cursor()

    # Add sample movies with is_active flag
    movies = [
        ("The Amazing Spiderman", "Hall 1", "10:00 AM"),
        ("The Godfather", "Hall 2", "01:00 PM"),
        ("The Dark Knight", "Hall 3", "04:00 PM"),
        ("Inception", "Hall 1", "04:00 PM"),
        ("Oppenheimer", "Hall 2", "10:00 AM")
    ]
    c.executemany('''INSERT OR IGNORE INTO movies (name, hall, time, is_active) VALUES (?, ?, ?, 1)''', movies)

    # Add seats for each movie
    c.execute('SELECT id FROM movies')
    movie_ids = [row[0] for row in c.fetchall()]
    for movie_id in movie_ids:
        for i in range(1, 21):  # Assuming 20 seats per movie
            c.execute('''
                INSERT OR IGNORE INTO seats (seat_number, booked, user_name, locked, movie_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (f'S{i}', False, None, False, movie_id))

    conn.commit()
    conn.close()

# %%
create_db()
initialize_movies_and_seats() 

# %%
import threading
# Lock to ensure thread safety
lock = threading.Lock()

# %%
def book_seat(seat_number, user_name, movie_id):
    with lock:
        conn = sqlite3.connect('Movie_Ticket_Booking_System.db', check_same_thread=False)
        cursor = conn.cursor()

        # Debug log
        print(f"Booking seat {seat_number} for movie_id {movie_id} by user {user_name}")

        # Scope the seat operation to the movie ID
        cursor.execute('SELECT booked, locked FROM seats WHERE seat_number = ? AND movie_id = ?', (seat_number, movie_id))
        seat = cursor.fetchone()

        if not seat:
            conn.close()
            return f"Seat {seat_number} not found for movie ID {movie_id}."

        if seat[1]:  # Seat is locked
            conn.close()
            return f"Seat {seat_number} is locked and cannot be booked!"
        elif seat[0]:  # Seat is already booked
            conn.close()
            return f"Seat {seat_number} is already booked!"
        else:
            # Book the seat for the selected movie
            cursor.execute('UPDATE seats SET booked = ?, user_name = ? WHERE seat_number = ? AND movie_id = ?',
                           (True, user_name, seat_number, movie_id))
            # Log the booking action
            cursor.execute('INSERT INTO logs (action, seat_number, user_name, movie_id) VALUES (?, ?, ?, ?)',
                           ('Booked', seat_number, user_name, movie_id))
            conn.commit()
        conn.close()
    return None


# %%
def toggle_lock_seat(seat_number, movie_id):
    with lock:
        conn = sqlite3.connect('Movie_Ticket_Booking_System.db', check_same_thread=False)
        cursor = conn.cursor()

        # Fetch the lock state for the seat specific to the movie
        cursor.execute('''SELECT locked 
                          FROM seats 
                          WHERE seat_number = ? AND movie_id = ?''', 
                       (seat_number, movie_id))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return f"Seat {seat_number} not found for movie ID {movie_id}."

        current_lock = result[0]
        new_lock = not current_lock  # Toggle lock state

        # Update the lock state for the specific movie
        cursor.execute('''UPDATE seats 
                          SET locked = ? 
                          WHERE seat_number = ? AND movie_id = ?''',
                       (new_lock, seat_number, movie_id))
        
        action = 'Locked' if new_lock else 'Unlocked'

        # Log the lock action
        cursor.execute('''INSERT INTO logs 
                          (action, seat_number, movie_id) 
                          VALUES (?, ?, ?)''', 
                       (action, seat_number, movie_id))
        
        conn.commit()
        conn.close()
    return new_lock


# %%
import tkinter as tk
from tkinter import simpledialog, messagebox

# %%
def reset_single_seat(self):
    if not self.selected_movie_id:
        messagebox.showwarning("Warning", "Please select a movie first.")
        return

    seat_to_reset = simpledialog.askstring("Reset Single Seat", "Enter seat number to reset:")
    if seat_to_reset in self.buttons:
        # Add a new method to reset a single seat
        conn = sqlite3.connect('Movie_Ticket_Booking_System.db')
        cursor = conn.cursor()
        
        # Reset the specific seat for the selected movie
        cursor.execute('''UPDATE seats 
                          SET booked = ?, user_name = ?, locked = ? 
                          WHERE seat_number = ? AND movie_id = ?''', 
                       (False, None, False, seat_to_reset, self.selected_movie_id))
        
        # Log the reset action
        cursor.execute('''INSERT INTO logs (action, seat_number, movie_id) 
                          VALUES (?, ?, ?)''', 
                       ('Reset', seat_to_reset, self.selected_movie_id))
        
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Admin Action", f"Seat {seat_to_reset} has been reset.")
    else:
        messagebox.showerror("Error", "Invalid seat number.")



# %%
def reset_seats(movie_id):
    conn = sqlite3.connect('Movie_Ticket_Booking_System.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''UPDATE seats SET booked = ?, user_name = ?, locked = ? WHERE movie_id = ?''', (False, None, False, movie_id))
    c.execute('''DELETE FROM logs WHERE movie_id = ?''', (movie_id,))
    conn.commit()
    conn.close()


# %%
def get_seat_data(movie_id):
    conn = sqlite3.connect('Movie_Ticket_Booking_System.db', check_same_thread=False)
    c = conn.cursor()
    # Explicitly filter seats by the specific movie_id
    c.execute('''SELECT seat_number, booked, user_name, locked 
                 FROM seats 
                 WHERE movie_id = ?''', (movie_id,))
    seats = c.fetchall()
    conn.close()
    return seats

# %%
def get_movie_list():
    conn = sqlite3.connect('Movie_Ticket_Booking_System.db', check_same_thread=False)
    c = conn.cursor()
    # Only fetch active movies
    c.execute('SELECT id, name, hall, time FROM movies WHERE is_active = 1 OR is_active IS NULL')
    movies = c.fetchall()
    conn.close()
    return movies

# %%
def add_movie_to_list(name, hall, time):
    try:
        conn = sqlite3.connect('Movie_Ticket_Booking_System.db')
        cursor = conn.cursor()

        # Check if the movie already exists in the database
        cursor.execute("SELECT COUNT(*) FROM movies WHERE name = ? AND hall = ? AND time = ?", (name, hall, time))
        exists = cursor.fetchone()[0]

        if exists:
            conn.close()
            return False, f"Movie '{name}' in hall '{hall}' at time '{time}' already exists. Ignored."

        # Insert the new movie
        cursor.execute("INSERT INTO movies (name, hall, time) VALUES (?, ?, ?)", (name, hall, time))
        conn.commit()

        # Get the new movie ID
        cursor.execute('SELECT id FROM movies WHERE name = ? AND hall = ? AND time = ?', (name, hall, time))
        new_movie_id = cursor.fetchone()[0]

        # Initialize seats for the new movie
        for i in range(1, 21):  # Assuming 20 seats per movie
            # Check if a seat with this number already exists for other movies
            cursor.execute('''
                INSERT OR IGNORE INTO seats (seat_number, booked, user_name, locked, movie_id) 
                VALUES (?, ?, ?, ?, ?)
            ''', (f'S{i}', False, None, False, new_movie_id))

        conn.commit()
        conn.close()

        # Notify all user interfaces about the new movie
        return True, f"Movie '{name}' added successfully."
    except Exception as e:
        return False, f"Error adding movie: {e}"





# %%
def remove_movie_from_list(movie_id):
    try:
        conn = sqlite3.connect('Movie_Ticket_Booking_System.db')  
        cursor = conn.cursor()

        # Check if the movie exists
        cursor.execute("SELECT name FROM movies WHERE id = ?", (movie_id,))
        movie_result = cursor.fetchone()

        if not movie_result:
            conn.close()
            return False, f"Movie with ID {movie_id} does not exist."
        
        movie_name = movie_result[0]

        # Soft delete: Mark the movie as inactive instead of deleting
        cursor.execute("UPDATE movies SET is_active = 0 WHERE id = ?", (movie_id,))
        
        # Optional: Log the movie removal
        cursor.execute('''INSERT INTO logs (action, seat_number, movie_id) 
                          VALUES (?, ?, ?)''', 
                       ('Movie Removed', movie_name, movie_id))
        
        conn.commit()
        conn.close()
        return True, f"Movie '{movie_name}' marked as inactive."
    
    except Exception as e:
        return False, f"Error removing movie: {e}"

# %%
# Generate Logs Tracker
def generate_logs():
    conn = sqlite3.connect('Movie_Ticket_Booking_System.db', check_same_thread=False)
    c = conn.cursor()

    # Fetch logs
    c.execute('SELECT action, seat_number, user_name, timestamp FROM logs ORDER BY timestamp')
    logs = c.fetchall()

    # Print log details
    print("\nSession Logs Summary:")
    if not logs:
        print("No actions were performed during this session.")
    else:
        for log in logs:
            action, seat_number, user_name, timestamp = log
            if user_name:
                print(f"[{timestamp}] {user_name} performed '{action}' on {seat_number}.")
            else:
                print(f"[{timestamp}] Admin performed '{action}' on {seat_number}.")

    # Seat states
    c.execute('SELECT seat_number, booked, user_name, locked FROM seats')
    seats = c.fetchall()
    print("\nFinal Seat States:")
    for seat in seats:
        seat_number, booked, user_name, locked = seat
        status = (
            f"Locked" if locked else
            f"Booked by {user_name}" if booked else
            "Available"
        )
        print(f"{seat_number}: {status}")

    conn.close()


# %%
def book_seat_thread(seat_number, user_name, movie_id):
    def task():
        error = book_seat(seat_number, user_name, movie_id)
        if error:
            messagebox.showerror("Error", error)
    threading.Thread(target=task).start()




# %%
def toggle_lock_seat_thread(seat_number, movie_id):
    def task():
        result = toggle_lock_seat(seat_number, movie_id)
        if isinstance(result, str):  # Check for error messages
            messagebox.showerror("Error", result)
        else:
            state = "locked" if result else "unlocked"
            messagebox.showinfo("Admin Action", f"Seat {seat_number} is now {state}.")
    threading.Thread(target=task).start()




# %%
class BookingGUI:
    def __init__(self, root, user_type, user_name=None):
        self.root = root
        self.user_type = user_type
        self.user_name = user_name
        self.buttons = {}
        self.selected_movie_id = None

        self.root.title(f"{user_type} Window")
        self.root.configure(bg="#2c3e50")  # Modern dark background

        # Ensure movie selector is created for both user and admin
        if user_type in ["User", "Admin"]:
            self.create_movie_selector()

        self.create_grid()

        if self.user_type == "Admin":
            self.create_movie_management_section()

        # Add to user windows tracker if this is a user window
        if self.user_type == "User":
            user_windows.append(self)

    def create_movie_selector(self):
        movies = get_movie_list()

        self.movie_var = tk.StringVar()
        self.movie_var.set("Select a Movie")

        self.movie_dropdown = tk.OptionMenu(
            self.root, self.movie_var,
            *[f"{name} ({hall} - {time})" for _, name, hall, time in movies],
            command=self.on_movie_selected
        )
        self.movie_dropdown.configure(
            bg="#34495e", fg="white", font=("Arial", 12),
            activebackground="#1abc9c", activeforeground="white"
        )
        self.movie_dropdown.grid(row=0, columnspan=5, pady=20)

        # Store the widget name for easier updates
        self.movie_var.widget_name = self.movie_dropdown.winfo_name()
        self.movie_mapping = {
            f"{name} ({hall} - {time})": movie_id for movie_id, name, hall, time in movies
        }

        # Initial UI update
        self.root.after(100, self.periodic_ui_update)

    def periodic_ui_update(self):
        """Periodically update the UI"""
        try:
            self.update_ui()
        except Exception as e:
            print(f"Error in periodic update: {e}")
        finally:
            # Schedule next update
            self.root.after(1000, self.periodic_ui_update)
            
    def update_ui(self):
        """Update the UI for seat states"""
        # Skip update if no movie is selected
        if not self.selected_movie_id:
            return

        try:
            # Fetch seat data for the selected movie
            seats = get_seat_data(self.selected_movie_id)
            
            for seat_number, button in self.buttons.items():
                # Default to available
                button.config(bg="#ecf0f1", text=f"{seat_number}\nAvailable", fg="#2c3e50")

            for seat in seats:
                seat_number, booked, user_name, locked = seat

                if locked:
                    self.buttons[seat_number].config(bg="#e74c3c", text=f"{seat_number}\nLocked", fg="white")
                elif booked:
                    if self.user_type == "Admin":  # Show the user name for the admin
                        self.buttons[seat_number].config(
                            bg="#1abc9c", text=f"{seat_number}\nBooked by\n{user_name}", fg="white"
                        )
                    else:
                        self.buttons[seat_number].config(bg="#1abc9c", text=f"{seat_number}\nBooked", fg="white")

        except Exception as e:
            print(f"Error updating UI: {e}")


    def on_movie_selected(self, selection):
        # Ensure the selection is not the default text
        if selection == "Select a Movie":
            print("Default movie selection, returning")
            return

        # Find the corresponding movie_id
        try:
            self.selected_movie_id = self.movie_mapping[selection]
            print(f"Selected movie_id: {self.selected_movie_id}")  # Debug print
        except KeyError:
            print(f"Error: Movie {selection} not found in mapping")
            messagebox.showerror("Error", "Could not find the selected movie")
            return
        # Find the corresponding movie_id
        self.selected_movie_id = self.movie_mapping[selection]

        # Debugging: Print selected movie_id for verification
        print(f"Selected movie_id: {self.selected_movie_id}")

        # Reset all seat buttons to default state first
        for seat_number, button in self.buttons.items():
            button.config(bg="#ecf0f1", text=f"{seat_number}\nAvailable", fg="#2c3e50")

        # Fetch and update only the seats for the selected movie
        seats = get_seat_data(self.selected_movie_id)
        
        for seat in seats:
            seat_number, booked, user_name, locked = seat

            if locked:
                self.buttons[seat_number].config(bg="#e74c3c", text=f"{seat_number}\nLocked", fg="white")
            elif booked:
                if self.user_type == "Admin":  # Show the user name for the admin
                    self.buttons[seat_number].config(
                        bg="#1abc9c", text=f"{seat_number}\nBooked by\n{user_name}", fg="white"
                    )
                else:
                    self.buttons[seat_number].config(bg="#1abc9c", text=f"{seat_number}\nBooked", fg="white")


    def create_grid(self):
        for i in range(1, 21):  # 20 seats
            btn = tk.Button(
                self.root, text=f"S{i}", width=10, height=2,
                command=lambda i=i: self.on_seat_click(f"S{i}"),
                bg="#ecf0f1", fg="#2c3e50", font=("Arial", 10, "bold")
            )
            btn.grid(row=(i-1)//5 + 1, column=(i-1)%5, padx=10, pady=10)
            self.buttons[f"S{i}"] = btn

        if self.user_type == "Admin":
            reset_btn = tk.Button(
                self.root, text="Reset All Seats", command=self.reset_all_seats,
                bg="#e74c3c", fg="white", font=("Arial", 12, "bold")
            )
            reset_btn.grid(row=5, columnspan=5, pady=20)

            reset_single_btn = tk.Button(
                self.root, text="Reset Single Seat", command=self.reset_single_seat,
                bg="#e74c3c", fg="white", font=("Arial", 12, "bold")
            )
            reset_single_btn.grid(row=6, columnspan=5, pady=20)

    def create_movie_management_section(self):
        # Section to add a new movie
        tk.Label(
            self.root, text="Add New Movie", bg="#2c3e50", fg="white",
            font=("Arial", 12, "bold")
        ).grid(row=7, columnspan=5, pady=10)

        self.new_movie_name = tk.Entry(self.root, width=20)
        self.new_movie_name.insert(0, "Movie Name")
        self.new_movie_name.grid(row=8, column=0, padx=5)

        self.new_movie_hall = tk.Entry(self.root, width=10)
        self.new_movie_hall.insert(0, "Hall")
        self.new_movie_hall.grid(row=8, column=1, padx=5)

        self.new_movie_time = tk.Entry(self.root, width=10)
        self.new_movie_time.insert(0, "Time")
        self.new_movie_time.grid(row=8, column=2, padx=5)

        add_movie_btn = tk.Button(
            self.root, text="Add Movie", command=self.add_movie,
            bg="#1abc9c", fg="white", font=("Arial", 10, "bold")
        )
        add_movie_btn.grid(row=8, column=3, padx=5)

        # Section to remove a movie
        tk.Label(
            self.root, text="Remove Movie", bg="#2c3e50", fg="white",
            font=("Arial", 12, "bold")
        ).grid(row=9, columnspan=5, pady=10)

        movies = get_movie_list()
        self.remove_movie_var = tk.StringVar()
        self.remove_movie_var.set("Select a Movie")

        self.remove_movie_dropdown = tk.OptionMenu(
            self.root, self.remove_movie_var,
            *[f"{name} ({hall} - {time})" for _, name, hall, time in movies]
        )
        self.remove_movie_dropdown.configure(
            bg="#34495e", fg="white", font=("Arial", 12),
            activebackground="#1abc9c", activeforeground="white"
        )
        self.remove_movie_dropdown.grid(row=10, columnspan=3, pady=10)

        # Store the widget name for easier updates
        self.remove_movie_var.widget_name = self.remove_movie_dropdown.winfo_name()

        remove_movie_btn = tk.Button(
            self.root, text="Remove Movie", command=self.remove_movie,
            bg="#e74c3c", fg="white", font=("Arial", 10, "bold")
        )
        remove_movie_btn.grid(row=10, column=3, padx=5)




    def add_movie(self):
        name = self.new_movie_name.get()
        hall = self.new_movie_hall.get()
        time = self.new_movie_time.get()

        if name and hall and time:
            success, message = add_movie_to_list(name, hall, time)
            if success:
                messagebox.showinfo("Success", message)
                
                # Clear input fields
                self.new_movie_name.delete(0, tk.END)
                self.new_movie_hall.delete(0, tk.END)
                self.new_movie_time.delete(0, tk.END)
                
                # Update movie selectors for ALL windows (admin and users)
                for window in user_windows + [self]:
                    window.update_movie_selector()
                    
                # Force a complete UI refresh
                self.root.update()
            else:
                messagebox.showerror("Error", message)
        else:
            messagebox.showerror("Error", "All fields are required to add a movie.")


    def remove_movie(self):
        selection = self.remove_movie_var.get()
        if selection != "Select a Movie":
            movie_id = self.movie_mapping[selection]
            success, message = remove_movie_from_list(movie_id)
            if success:
                messagebox.showinfo("Success", message)
                
                # Reset seat display and movie selector for all windows
                self.update_movie_selector()
                
                # Update all user windows
                for user_gui in user_windows:
                    user_gui.update_movie_selector()
                    
                # Force UI updates
                self.root.update()
                for user_gui in user_windows:
                    user_gui.root.update()
            else:
                messagebox.showerror("Error", message)
        else:
            messagebox.showerror("Error", "Please select a movie to remove.")
            
    def reset_seat_ui(self):
        # Reset all seat buttons to default state
        for seat_number, button in self.buttons.items():
            button.config(bg="#ecf0f1", text=f"{seat_number}\nAvailable", fg="#2c3e50")
        
        # Force a UI update
        if self.selected_movie_id:
            self.update_ui()
            
    def update_movie_selector(self):
        movies = get_movie_list()  # Fetch updated movie list

        # Clear the current movie dropdown menu
        dropdown_menu = self.root.nametowidget(self.movie_var.widget_name).children["menu"]
        dropdown_menu.delete(0, "end")  # Clear the current menu items

        # Recreate the movie mapping with full labels
        self.movie_mapping = {f"{name} ({hall} - {time})": movie_id for movie_id, name, hall, time in movies}

        # Add new menu items
        for label in self.movie_mapping.keys():
            dropdown_menu.add_command(
                label=label, 
                command=lambda value=label: self.on_movie_selected(value)  # Use on_movie_selected directly
            )

        # Reset the movie selection visually
        self.movie_var.set("Select a Movie")

        # Reset all seat buttons to default state
        for seat_number, button in self.buttons.items():
            button.config(bg="#ecf0f1", text=f"{seat_number}\nAvailable", fg="#2c3e50")

        # Update the movie dropdown in the remove section (Admin only)
        if self.user_type == "Admin":
            remove_menu = self.root.nametowidget(self.remove_movie_var.widget_name).children["menu"]
            remove_menu.delete(0, "end")  # Clear the current menu items
            
            # Recreate remove movie mapping and menu items
            for label in self.movie_mapping.keys():
                remove_menu.add_command(
                    label=label, 
                    command=lambda value=label: self.remove_movie_var.set(value)
                )
            
            # Reset the remove movie selection
            self.remove_movie_var.set("Select a Movie")

    def on_seat_click(self, seat_number):
        if not self.selected_movie_id and self.user_type == "User":
            messagebox.showwarning("Warning", "Please select a movie first.")
            return

        if self.user_type == "Admin":
            toggle_lock_seat_thread(seat_number, self.selected_movie_id)
        elif self.user_name:
            book_seat_thread(seat_number, self.user_name, self.selected_movie_id)


    def reset_all_seats(self):
        if not self.selected_movie_id:
            messagebox.showwarning("Warning", "Please select a movie first.")
            return

        reset_seats(self.selected_movie_id)  # Pass selected movie_id to reset_seats
        messagebox.showinfo("Admin Action", "All seats have been reset.")

    def reset_single_seat(self):
        if not self.selected_movie_id:
            messagebox.showwarning("Warning", "Please select a movie first.")
            return

        seat_to_reset = simpledialog.askstring("Reset Single Seat", "Enter seat number to reset:")
        if seat_to_reset in self.buttons:
            # Add a new method to reset a single seat
            conn = sqlite3.connect('Movie_Ticket_Booking_System.db')
            cursor = conn.cursor()

            # Reset the specific seat for the selected movie
            cursor.execute('''UPDATE seats 
                              SET booked = ?, user_name = ?, locked = ? 
                              WHERE seat_number = ? AND movie_id = ?''', 
                           (False, None, False, seat_to_reset, self.selected_movie_id))

            # Log the reset action
            cursor.execute('''INSERT INTO logs (action, seat_number, movie_id) 
                              VALUES (?, ?, ?)''', 
                           ('Reset', seat_to_reset, self.selected_movie_id))

            conn.commit()
            conn.close()

            messagebox.showinfo("Admin Action", f"Seat {seat_to_reset} has been reset.")
        else:
            messagebox.showerror("Error", "Invalid seat number.")
    
        # Optional: only schedule further updates if there's no critical error
        self.root.after(1000, self.update_ui)



# %%


# %%
# Main Function
def main():


    # Prompt for user names
    root = tk.Tk()
    user1_name = simpledialog.askstring("Input", "Enter name for User 1:", parent=root)
    user2_name = simpledialog.askstring("Input", "Enter name for User 2:", parent=root)

    if not user1_name or not user2_name:
        messagebox.showerror("Error", "User names are required to proceed.")
        return

    # Admin GUI
    admin_window = tk.Toplevel(root)
    admin_gui = BookingGUI(admin_window, user_type="Admin")
    

    # Create separate windows for User 1 and User 2
    def launch_user_gui(user_name):
        user_window = tk.Toplevel(root)
        gui = BookingGUI(user_window, user_type="User", user_name=user_name)
        user_window.protocol("WM_DELETE_WINDOW", lambda: user_window.destroy())

    # Launch user windows in separate threads for concurrency
    user1_thread = threading.Thread(target=launch_user_gui, args=(user1_name,))
    user2_thread = threading.Thread(target=launch_user_gui, args=(user2_name,))
    user1_thread.start()
    user2_thread.start()

    root.mainloop()

    # Generate logs after the session ends
    generate_logs()


# %%
if __name__ == "__main__":
    main()

# %%
'''
import time
import threading

# Simulating the seat booking functions for demonstration purposes
def book_seat(seat_number, user_name):
    # Simulate seat booking process (single-threaded)
    time.sleep(0.1)  # Simulate some work being done (e.g., network or DB operation)
    print(f"Seat {seat_number} booked by {user_name}.")

def book_seat_thread(seat_number, user_name):
    # Simulate seat booking in a separate thread
    threading.Thread(target=book_seat, args=(seat_number, user_name)).start()

# Measure and Compare Performance (Single-Threaded vs. Multi-Threaded)
def measure_performance():
    # Time single-threaded booking
    start_time = time.time()
    for i in range(1, 21):  # 20 seats
        book_seat(f"S{i}", "User")
    single_threaded_time = time.time() - start_time

    # Time multi-threaded booking
    start_time = time.time()
    threads = []
    for i in range(1, 21):  # 20 seats
        thread = threading.Thread(target=book_seat, args=(f"S{i}", "User"))
        thread.start()
        threads.append(thread)
    
    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    multi_threaded_time = time.time() - start_time

    # Print the results
    print(f"Single-threaded execution time: {single_threaded_time:.4f} seconds")
    print(f"Multithreaded execution time: {multi_threaded_time:.4f} seconds")

    # Compare and print the performance results
    if multi_threaded_time < single_threaded_time:
        print(f"Multithreading is {single_threaded_time / multi_threaded_time:.2f} times faster.")
    else:
        print(f"Multithreading is {multi_threaded_time / single_threaded_time:.2f} times slower.")

# Call the function to measure performance
measure_performance()
'''

# %%



