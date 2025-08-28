import csv
import os

import tkinter as tk
from tkinter import ttk

class player_new:
    def __init__(self, name, game, number_of_games, wins, record):
        self.name = name
        self.game = game
        self.number_of_games = number_of_games
        self.wins = wins
        self.record = record


class scoreboard_new:
    def create_database():
        file = "Scoreboard.csv"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(base_dir, file)
        with open(filename, "a", newline = "") as file:
            writer = csv.writer(file)
            writer.writerow(["Name", "Game", "Number of games", "Wins", "Record"])
            return ("Database created!")

    def getStats(player: player_new):
        file = "Scoreboard.csv"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(base_dir, file)
        found = False
        if not os.path.exists(filename):
            with open(filename, "a", newline = "") as file:
                writer = csv.writer(file)
                writer.writerow(["Name", "Game", "Number of games", "Wins", "Record"])
            with open(filename, "a", newline = "") as file:
                writer = csv.writer(file)
                writer.writerow([player.name, player.game, player.number_of_games, player.wins, player.record])
                return ("Database created!")
        else:
            with open(filename, "r", newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row["Name"] == player.name and row["Game"] == player.game:
                        found = True
                        return {
                        "number of games": row["Number of games"],
                        "wins": row["Wins"],
                        "record": row["Record"]}
            if not found:
                with open(filename, "a", newline = "") as file:
                    writer = csv.writer(file)
                    writer.writerow([player.name, player.game, player.number_of_games, player.wins, player.record])
                    return ("Player created!")
                
    def get_names():
        file = "Scoreboard.csv"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(base_dir, file)
        names = []
        if os.path.exists(filename):
            with open(filename, "r", newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row["Name"]:
                        names.append(row["Name"])

                return names
        else:
            return scoreboard_new.create_database()
                
    def save(player: player_new):
        file = "Scoreboard.csv"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(base_dir, file)
        found = False
        rows = []
        with open(filename, "r", newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                rows.append(row)
                for row in rows:
                    if row["Name"] == player.name and row["Game"] == player.game:
                        found = True
                        row["Number of games"] = player.number_of_games
                        row["Wins"] = player.wins
                        row["Record"] = player.record

            with open(filename, "w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["Name", "Game", "Number of games", "Wins", "Record"])
                writer.writeheader()
                writer.writerows(rows)
            return "Player was updated!"
        if not found:
           return "Player could not be found!"
        
    def get_all_stats(self):
        file = "Scoreboard.csv"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(base_dir, file)

        if not os.path.exists(filename):
            with open(filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Game", "Number of games", "Wins", "Record"])
            return []

        stats = []
        with open(filename, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                stats.append(row)
        return stats


class GameStatGui:
    def __init__(self, root, stat_manager):
        self.root = root
        self.root.eval('tk::PlaceWindow . center')
        self.root.title("Game Stats")
        self.stat_manager = stat_manager

        self.frame = ttk.Frame(root, padding=10) 
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.label = ttk.Label(self.frame, text="Game Stats", font=("Helvetica", 16))
        self.label.pack(pady=5)

        self.listbox = tk.Listbox(self.frame, width=70, height=20)
        self.listbox.pack(pady=5 , expand = True)

        self.load_stats()

        self.refresh_button = ttk.Button(self.frame, text="Refresh Stats", command=self.load_stats)
        self.refresh_button.pack(pady=5)

        self.load_stats()

    def load_stats(self):
        self.listbox.delete(0, tk.END)
        stats = self.stat_manager.get_all_stats()
        for row in stats:
            display = f"{row['Name']} - {row['Game']} : {row['Number of games']} Games, {row['Wins']} wins"
            self.listbox.insert(tk.END, display)


if __name__ == "__main__":
    root = tk.Tk()
    manager = scoreboard_new()
    gui = GameStatGui(root, manager)
    root.mainloop()
