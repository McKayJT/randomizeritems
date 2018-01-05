#!/usr/bin/env python

from tkinter import *
from tkinter import ttk
from tkinter import font
from PIL import Image
from PIL import ImageTk
from PIL import ImageOps
from math import *
import json
import time

class RandomizerItems(Tk):
    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)

        Tk.wm_title(self, "Randomizer Items")
        Tk.resizable(self, FALSE, FALSE)
        self.imageLabels = []
        self.createLayout()
        self.reset()

    def createLayout(self):
        configFile = open("config.json")
        config = json.load(configFile)

        imageSize = config["size"]
        columns = config["columns"]

        container = ttk.Frame(self)
        container.grid(column = 0, row = 0, sticky=(N, W, E, S))

        resetButton = ttk.Button(container, text="Reset", command=self.reset)
        resetButton.grid(column=0, row=0, columnspan=floor(columns/2),
                         sticky=(W), pady=10, padx=10)

        self.startButton = ttk.Button(container, text="Start", command=self.start)
        self.startButton.grid(column=floor(columns/2),row=0, columnspan=floor(columns/2),
                              sticky=(E),pady=10, padx=10)

        self.timeCount = StringVar()
        timerFont = font.Font(**config["timerfont"])
        timerLabel = ttk.Label(container, textvariable=self.timeCount,
                               font=timerFont, foreground=config["timercolor"])
        timerLabel.grid(column=0, row=1, columnspan=columns, sticky=(E))

        maxrows = 0
        for index, images in enumerate(config["imagelist"]):

            row = 2 + floor(index / columns)
            if row > maxrows:
                maxrows = row

            column = index % columns
            label = ToggleImageLabel(container, images, imageSize)
            label.grid(column=column, row=row, sticky=(W))
            self.imageLabels.append(label)

    def reset(self):
        self.timerRunning = False
        self.timeCount.set("00:00.0")
        self.startButton["text"] = "Start"
        self.startButton["command"] = self.start
        for label in self.imageLabels:
            label.reset()

    def start(self):
        self.startTime = time.monotonic()
        self.timerRunning = True
        self.startButton["command"] = self.stop
        self.startButton["text"] = "Stop"
        self.updateTimer()

    def restart(self):
        self.startTime = time.monotonic() - self.passed
        self.timerRunning = True
        self.startButton["command"] = self.stop
        self.startButton["text"] = "Stop"
        self.updateTimer()

    def stop(self):
        self.timerRunning = False
        self.startButton["text"] = "Restart"
        self.startButton["command"] = self.restart

    def updateTimer(self):
        if not self.timerRunning:
            return
        self.passed = time.monotonic() - self.startTime
        seconds = floor(self.passed) % 60
        minutes = floor(floor(self.passed) % (60 * 60) / 60)
        hours = floor(floor(self.passed) % (60 * 60 * 60) / (60 * 60))
        fract = self.passed - floor(self.passed)
        if hours > 0: 
            self.timeCount.set("%d:%02d:%02d.%01d" % (hours, minutes, seconds, (fract * 10)))
        else:
            self.timeCount.set("%02d:%02d.%01d" % (minutes, seconds, (fract * 10)))
        self.after(100, self.updateTimer)

class ToggleImageLabel(ttk.Label):

    def __init__(self, container, imagelist, size):
        ttk.Label.__init__(self, container)
        # we have to keep a copy of every image in this list
        # or it will be garbage collected and not display due to a PIL bug
        self.images = []
        self.currentImage = 0

        self.bind('<ButtonPress>', lambda e: self.switchImage(e))
        for image in imagelist["images"]:
            tkimg = ImageTk.PhotoImage(Image.open(image).resize(size))
            self.images.append(tkimg)

        self["image"] = self.images[self.currentImage]

    def switchImage(self, event):

        if event.num == 1:
            self.currentImage += 1
        elif event.num == 3:
            self.currentImage -= 1

        if self.currentImage < 0:
            self.currentImage = len(self.images) - 1
        elif self.currentImage == len(self.images):
            self.currentImage = 0

        self["image"] = self.images[self.currentImage]

    def reset(self):
        self.currentImage = 0
        self["image"] = self.images[self.currentImage]


randomizer = RandomizerItems(className="randomizer items")

randomizer.mainloop()

# vim: ai:et:ts=4:sw=4
