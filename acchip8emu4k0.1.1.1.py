import tkinter as tk
from tkinter import filedialog, messagebox
import random
import pickle
import os

WIDTH, HEIGHT = 600, 400
SCREEN_W, SCREEN_H = 64, 32
PIXEL = 8

BLUE = "#00BFFF"
DARK_BLUE = "#002850"
BLACK = "#000000"

FONTSET = [
    0xF0,0x90,0x90,0x90,0xF0, 0x20,0x60,0x20,0x20,0x70,
    0xF0,0x10,0xF0,0x80,0xF0, 0xF0,0x10,0xF0,0x10,0xF0,
    0x90,0x90,0xF0,0x10,0x10, 0xF0,0x80,0xF0,0x10,0xF0,
    0xF0,0x80,0xF0,0x90,0xF0, 0xF0,0x10,0x20,0x40,0x40,
    0xF0,0x90,0xF0,0x90,0xF0, 0xF0,0x90,0xF0,0x10,0xF0,
    0xF0,0x90,0xF0,0x90,0x90, 0xE0,0x90,0xE0,0x90,0xE0,
    0xF0,0x80,0x80,0x80,0xF0, 0xE0,0x90,0x90,0x90,0xE0,
    0xF0,0x80,0xF0,0x80,0xF0, 0xF0,0x80,0xF0,0x80,0x80
]

KEYMAP = {
    "1": 0x1, "2": 0x2, "3": 0x3, "4": 0xC,
    "q": 0x4, "w": 0x5, "e": 0x6, "r": 0xD,
    "a": 0x7, "s": 0x8, "d": 0x9, "f": 0xE,
    "z": 0xA, "x": 0x0, "c": 0xB, "v": 0xF,
}

class Chip8:
    def __init__(self):
        self.reset()

    def reset(self):
        self.memory = [0] * 4096
        self.v = [0] * 16
        self.i = 0
        self.pc = 0x200
        self.stack = []
        self.delay = 0
        self.sound = 0
        self.keys = [0] * 16
        self.screen = [[0] * SCREEN_W for _ in range(SCREEN_H)]
        self.rom_path = None
        for n, byte in enumerate(FONTSET):
            self.memory[0x50 + n] = byte

    def load_rom(self, path):
        self.reset()
        self.rom_path = path
        with open(path, "rb") as f:
            data = f.read()
        for n, byte in enumerate(data[:4096 - 0x200]):
            self.memory[0x200 + n] = byte

    def save_state(self, path):
        with open(path, "wb") as f:
            pickle.dump(self.__dict__, f)

    def load_state(self, path):
        with open(path, "rb") as f:
            self.__dict__.update(pickle.load(f))

    def cycle(self):
        op = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc = (self.pc + 2) & 0xFFF

        x = (op & 0x0F00) >> 8
        y = (op & 0x00F0) >> 4
        n = op & 0x000F
        nn = op & 0x00FF
        nnn = op & 0x0FFF

        if op == 0x00E0:
            self.screen = [[0] * SCREEN_W for _ in range(SCREEN_H)]
        elif op == 0x00EE:
            if self.stack:
                self.pc = self.stack.pop()
        elif op & 0xF000 == 0x1000:
            self.pc = nnn
        elif op & 0xF000 == 0x2000:
            self.stack.append(self.pc)
            self.pc = nnn
        elif op & 0xF000 == 0x3000:
            if self.v[x] == nn:
                self.pc += 2
        elif op & 0xF000 == 0x4000:
            if self.v[x] != nn:
                self.pc += 2
        elif op & 0xF00F == 0x5000:
            if self.v[x] == self.v[y]:
                self.pc += 2
        elif op & 0xF000 == 0x6000:
            self.v[x] = nn
        elif op & 0xF000 == 0x7000:
            self.v[x] = (self.v[x] + nn) & 0xFF
        elif op & 0xF00F == 0x8000:
            self.v[x] = self.v[y]
        elif op & 0xF00F == 0x8001:
            self.v[x] |= self.v[y]
        elif op & 0xF00F == 0x8002:
            self.v[x] &= self.v[y]
        elif op & 0xF00F == 0x8003:
            self.v[x] ^= self.v[y]
        elif op & 0xF00F == 0x8004:
            total = self.v[x] + self.v[y]
            self.v[0xF] = 1 if total > 255 else 0
            self.v[x] = total & 0xFF
        elif op & 0xF00F == 0x8005:
            self.v[0xF] = 1 if self.v[x] > self.v[y] else 0
            self.v[x] = (self.v[x] - self.v[y]) & 0xFF
        elif op & 0xF00F == 0x8006:
            self.v[0xF] = self.v[x] & 1
            self.v[x] >>= 1
        elif op & 0xF00F == 0x800E:
            self.v[0xF] = (self.v[x] >> 7) & 1
            self.v[x] = (self.v[x] << 1) & 0xFF
        elif op & 0xF00F == 0x9000:
            if self.v[x] != self.v[y]:
                self.pc += 2
        elif op & 0xF000 == 0xA000:
            self.i = nnn
        elif op & 0xF000 == 0xB000:
            self.pc = nnn + self.v[0]
        elif op & 0xF000 == 0xC000:
            self.v[x] = random.randint(0, 255) & nn
        elif op & 0xF000 == 0xD000:
            self.v[0xF] = 0
            for row in range(n):
                sprite = self.memory[self.i + row]
                for col in range(8):
                    if sprite & (0x80 >> col):
                        px = (self.v[x] + col) % SCREEN_W
                        py = (self.v[y] + row) % SCREEN_H
                        if self.screen[py][px]:
                            self.v[0xF] = 1
                        self.screen[py][px] ^= 1
        elif op & 0xF0FF == 0xE09E:
            if self.keys[self.v[x]]:
                self.pc += 2
        elif op & 0xF0FF == 0xE0A1:
            if not self.keys[self.v[x]]:
                self.pc += 2
        elif op & 0xF0FF == 0xF007:
            self.v[x] = self.delay
        elif op & 0xF0FF == 0xF015:
            self.delay = self.v[x]
        elif op & 0xF0FF == 0xF018:
            self.sound = self.v[x]
        elif op & 0xF0FF == 0xF01E:
            self.i = (self.i + self.v[x]) & 0xFFF
        elif op & 0xF0FF == 0xF029:
            self.i = 0x50 + self.v[x] * 5
        elif op & 0xF0FF == 0xF033:
            val = self.v[x]
            self.memory[self.i] = val // 100
            self.memory[self.i + 1] = (val // 10) % 10
            self.memory[self.i + 2] = val % 10
        elif op & 0xF0FF == 0xF055:
            for r in range(x + 1):
                self.memory[self.i + r] = self.v[r]
        elif op & 0xF0FF == 0xF065:
            for r in range(x + 1):
                self.v[r] = self.memory[self.i + r]

    def tick_timers(self):
        if self.delay > 0:
            self.delay -= 1
        if self.sound > 0:
            self.sound -= 1

class Chip8EmuByAC(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("chip8emubyac")
        self.geometry(f"{WIDTH}x{HEIGHT}")
        self.resizable(False, False)
        self.configure(bg=BLACK)

        self.chip = Chip8()
        self.running_rom = False
        self.paused = False
        self.cycles_per_frame = 10

        self.make_menu()

        self.canvas = tk.Canvas(self, width=WIDTH, height=HEIGHT, bg=BLACK, highlightthickness=0)
        self.canvas.pack()

        self.bind("<KeyPress>", self.key_down)
        self.bind("<KeyRelease>", self.key_up)

        self.draw()
        self.loop()

    def make_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Load ROM", command=self.load_rom)
        file_menu.add_command(label="Play ROM", command=self.play_rom)
        file_menu.add_command(label="Pause / Resume", command=self.pause_resume)
        file_menu.add_separator()
        file_menu.add_command(label="Save State", command=self.save_state)
        file_menu.add_command(label="Load State", command=self.load_state)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        cheats_menu = tk.Menu(menubar, tearoff=0)
        cheats_menu.add_command(label="Clear Screen", command=self.cheat_clear)
        cheats_menu.add_command(label="Slow Mode", command=lambda: self.set_speed(3))
        cheats_menu.add_command(label="Normal Speed", command=lambda: self.set_speed(10))
        cheats_menu.add_command(label="Fast Mode", command=lambda: self.set_speed(30))
        menubar.add_cascade(label="Cheats", menu=cheats_menu)

        gamepad_menu = tk.Menu(menubar, tearoff=0)
        gamepad_menu.add_command(label="Show Controls", command=self.show_controls)
        menubar.add_cascade(label="Gamepad", menu=gamepad_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.about)
        menubar.add_cascade(label="About", menu=help_menu)

        self.config(menu=menubar)

    def load_rom(self):
        path = filedialog.askopenfilename(
            title="Load CHIP-8 ROM",
            filetypes=[("CHIP-8 ROMs", "*.ch8 *.rom *.bin"), ("All files", "*.*")]
        )
        if path:
            self.chip.load_rom(path)
            self.running_rom = True
            self.paused = False

    def play_rom(self):
        if not self.chip.rom_path:
            self.load_rom()
        else:
            self.running_rom = True
            self.paused = False

    def pause_resume(self):
        self.paused = not self.paused

    def save_state(self):
        path = filedialog.asksaveasfilename(
            title="Save State",
            defaultextension=".c8state",
            filetypes=[("CHIP8EMUByAC State", "*.c8state")]
        )
        if path:
            self.chip.save_state(path)

    def load_state(self):
        path = filedialog.askopenfilename(
            title="Load State",
            filetypes=[("CHIP8EMUByAC State", "*.c8state"), ("All files", "*.*")]
        )
        if path:
            self.chip.load_state(path)
            self.running_rom = True

    def cheat_clear(self):
        self.chip.screen = [[0] * SCREEN_W for _ in range(SCREEN_H)]

    def set_speed(self, speed):
        self.cycles_per_frame = speed

    def show_controls(self):
        messagebox.showinfo(
            "Gamepad / Keyboard",
            "CHIP-8 keypad:\n\n"
            "1 2 3 4\n"
            "Q W E R\n"
            "A S D F\n"
            "Z X C V\n\n"
            "Maps to CHIP-8 keys 0-F."
        )

    def about(self):
        messagebox.showinfo(
            "About chip8emubyac",
            "chip8emubyac\n"
            "A.C HOLDINGS\n\n"
            "Python 3.14 + Tkinter\n"
            "Blue text, black background\n"
            "mGBA-style menu strip"
        )

    def key_down(self, event):
        key = event.keysym.lower()
        if key in KEYMAP:
            self.chip.keys[KEYMAP[key]] = 1

    def key_up(self, event):
        key = event.keysym.lower()
        if key in KEYMAP:
            self.chip.keys[KEYMAP[key]] = 0

    def draw(self):
        self.canvas.delete("all")

        self.canvas.create_rectangle(8, 8, 592, 392, outline=DARK_BLUE, width=2)
        self.canvas.create_rectangle(8, 8, 592, 34, fill=DARK_BLUE, outline=DARK_BLUE)
        self.canvas.create_text(16, 21, anchor="w", fill=BLUE, font=("Courier", 11, "bold"),
                                text="chip8emubyac | A.C HOLDINGS | Tkinter GUI")

        ox, oy = 44, 58
        for y in range(SCREEN_H):
            for x in range(SCREEN_W):
                if self.chip.screen[y][x]:
                    self.canvas.create_rectangle(
                        ox + x * PIXEL,
                        oy + y * PIXEL,
                        ox + x * PIXEL + PIXEL - 1,
                        oy + y * PIXEL + PIXEL - 1,
                        fill=BLUE,
                        outline=BLUE
                    )

        status = "NO ROM"
        if self.running_rom:
            status = "PLAYING"
        if self.paused:
            status = "PAUSED"

        self.canvas.create_text(16, 360, anchor="w", fill=BLUE, font=("Courier", 10),
                                text=f"mGBA-ish GUI | bg=black | text=blue | {status}")

        if not self.chip.rom_path:
            self.canvas.create_text(16, 335, anchor="w", fill=BLUE, font=("Courier", 10),
                                    text="File > Load ROM   then   File > Play ROM")

    def loop(self):
        if self.running_rom and not self.paused:
            try:
                for _ in range(self.cycles_per_frame):
                    self.chip.cycle()
                self.chip.tick_timers()
            except Exception as e:
                self.running_rom = False
                messagebox.showerror("Emulator Error", str(e))

        self.draw()
        self.after(16, self.loop)

if __name__ == "__main__":
    app = Chip8EmuByAC()
    app.mainloop()
