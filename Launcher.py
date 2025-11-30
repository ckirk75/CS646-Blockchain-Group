# ---------------------------------------------------------
# tinydeck_game_launcher_combined.py
# ---------------------------------------------------------

import os
import sys
import json
import getpass
import subprocess
import requests
import random
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox


#  CONFIG

API_BASE = "http://localhost:4000"
GAME_ID = 8                    # Change to  DB game id
TITLE_PATH = r"G:\title_screen.png"   # Change if needed


#  LOGIN + ENTITLEMENT CHECK

def login(username: str, password: str):
    """Call /api/login and return user dict or None."""
    url = f"{API_BASE}/api/login"
    resp = requests.post(url, json={"username": username, "password": password})
    if resp.status_code != 200:
        print("Login failed:", resp.text)
        return None
    return resp.json()


def check_entitlement(user_id: int, game_id: int):
    """Call /api/entitlement/:userId/:gameId and return JSON."""
    url = f"{API_BASE}/api/entitlement/{user_id}/{game_id}"
    resp = requests.get(url)
    if resp.status_code != 200:
        print("Entitlement check failed:", resp.text)
        return {"authorized": False, "reason": "Server error"}

    return resp.json()


#  THE GAME 

class DeckGameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tiny Deck Game (v1.0.0)")

        # --- Title screen ---
        self.title_frame = tk.Frame(root, bg="black")
        self.title_frame.pack(fill="both", expand=True)

        img = Image.open(TITLE_PATH)
        self.title_img = ImageTk.PhotoImage(img)
        self.title_label = tk.Label(self.title_frame, image=self.title_img, bg="black")
        self.title_label.pack(expand=True)

        self.press_label = tk.Label(
            self.title_frame,
            text="PRESS ANY KEY TO START",
            fg="#ffffff",
            bg="black",
            font=("Consolas", 16)
        )
        self.press_label.pack(pady=20)

        # Listen for any key to start
        self.root.bind("<Key>", self.on_any_key)

        self.game_initialized = False

    def on_any_key(self, event):
        if not self.game_initialized:
            self.start_game()

    def start_game(self):
        self.root.unbind("<Key>")
        self.title_frame.destroy()
        self.build_game_ui()
        self.new_game()

    def build_game_ui(self):
        self.info_label = tk.Label(self.root, text="Draw cards and play 3 to reach 20+ points!")
        self.info_label.pack(pady=10)

        self.score_label = tk.Label(self.root, text="Score: 0 | Plays left: 3")
        self.score_label.pack(pady=5)

        self.hand_frame = tk.Frame(self.root)
        self.hand_frame.pack(pady=10)

        self.hand_buttons = []

        self.controls_frame = tk.Frame(self.root)
        self.controls_frame.pack(pady=10)

        self.draw_button = tk.Button(self.controls_frame, text="New Game", command=self.new_game)
        self.draw_button.grid(row=0, column=0, padx=5)

        self.quit_button = tk.Button(self.controls_frame, text="Quit", command=self.root.quit)
        self.quit_button.grid(row=0, column=1, padx=5)

        self.game_initialized = True

    def new_game(self):
        self.deck = [v for v in range(1, 11)] * 2
        random.shuffle(self.deck)

        self.plays_left = 3
        self.score = 0
        self.score_label.config(text=f"Score: {self.score} | Plays left: {self.plays_left}")
        self.info_label.config(text="Pick 3 cards from your hand to reach 20+ points!")

        self.draw_hand()

    def draw_hand(self):
        for btn in self.hand_buttons:
            btn.destroy()
        self.hand_buttons.clear()

        self.hand = []
        for _ in range(5):
            if self.deck:
                self.hand.append(self.deck.pop())

        for idx, value in enumerate(self.hand):
            btn = tk.Button(
                self.hand_frame,
                text=str(value),
                width=5,
                command=lambda i=idx: self.play_card(i)
            )
            btn.grid(row=0, column=idx, padx=5)
            self.hand_buttons.append(btn)

        if not self.hand and self.plays_left > 0:
            self.info_label.config(text="No more cards in deck!")
            self.end_round()

    def play_card(self, index):
        if self.plays_left <= 0:
            return

        value = self.hand[index]
        self.score += value
        self.plays_left -= 1

        self.hand_buttons[index].config(state=tk.DISABLED)
        self.score_label.config(text=f"Score: {self.score} | Plays left: {self.plays_left}")

        if self.plays_left == 0:
            self.end_round()
        else:
            if all(btn['state'] == tk.DISABLED for btn in self.hand_buttons):
                self.draw_hand()

    def end_round(self):
        if self.score >= 20:
            msg = f"You win! Score = {self.score}\n(Goal: 20+)"
        else:
            msg = f"You lose. Score = {self.score}\n(Goal: 20+)"

        messagebox.showinfo("Round Over", msg)
        self.info_label.config(text="Click 'New Game' to play again.")



#  MAIN: Login → License Check → Start Game


def main():
    print("=== Tiny Deck Launcher ===")
    print("Please log in with your store account.\n")

    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    user = login(username, password)
    if not user:
        input("Press Enter to exit...")
        return

    user_id = user.get("userId")
    print(f"Login OK. User ID = {user_id}")

    print(f"\nChecking license for game #{GAME_ID}...")
    ent = check_entitlement(user_id, GAME_ID)

    if not ent.get("authorized"):
        print("\n=== Access Denied ===")
        print(ent.get("reason", "No active license."))
        input("Press Enter to exit...")
        return

    game_name = ent.get("gameName", f"Game #{GAME_ID}")
    print(f"\nLicense OK. Enjoy {game_name}!")

    # Start the actual Tkinter game
    root = tk.Tk()
    app = DeckGameApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
