#!/usr/bin/env python

from tkinter import *
from tkinter import ttk
from tkinter import font
from PIL import Image
from PIL import ImageTk
from math import *
from collections import namedtuple
from queue import Queue
import json
import time
import socketserver
import sys
import os
import threading
import socket

class EmuDatagramHandler(socketserver.BaseRequestHandler):
    """
    Handles a message from the emulator

    Message type identified by one octet

    Current Message Types:
    'M': write to memory. Followed by 2 octets 'address'
         and one octet 'data'
    'A': ask for list of memory addresses to send write data from
         will send back 2 octet number of addresses, followed
         by the address list
    """
    def handle(self):
        req = self.request.recv(1024)
        reqtype = req[0]
        if reqtype == b'M'[0]:
            self.handleMemoryWrite(req[1:])
        elif reqtype == b'A'[0]:
            self.sendAddresses()
        else:
            print("Unsupported request: {}".format(req))

    def handleMemoryWrite(self, message):
        addr = int.from_bytes(message[0:2], byteorder=sys.byteorder)
        data = message[2]
        self.server.queue.put((addr, data))

    def sendAddresses(self):
        resp = bytearray()
        resp += len(self.server.addresses).to_bytes(2, byteorder=sys.byteorder)
        for address in self.server.addresses:
            resp += address.to_bytes(2, byteorder=sys.byteorder)
        self.request.sendto(resp, self.client_address)

class EmuDatagramServer(socketserver.UnixStreamServer):
    socket_type = socket.SOCK_SEQPACKET

    def __init__(self, *args, **kwargs):
        socketserver.UnixDatagramServer.__init__(self, *args, **kwargs)
        self.addresses = []
        self.queue = Queue()

class RandomizerItems(Tk):
    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)

        Tk.wm_title(self, "Randomizer Items")
        Tk.resizable(self, FALSE, FALSE)
        self.imageLabels = []
        self.addressListeners = {}
        self.createLayout()
        self.createListener()
        self.server_thread = threading.Thread(target=self.listener.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.reset()
        self.checkQueue()

    def createListener(self):
        socketpath = os.environ.get("XDG_RUNTIME_DIR", ".") + "/randomizer.sock"
        if os.path.exists(socketpath):
            os.remove(socketpath);
        self.listener = EmuDatagramServer(socketpath,EmuDatagramHandler)
        for address in self.addressListeners.keys():
            self.listener.addresses.append(address)

    def checkQueue(self):
        while not self.listener.queue.empty():
            address, value = self.listener.queue.get()
            if address in self.addressListeners:
                for callback in self.addressListeners[address]:
                    callback(value)
            self.listener.queue.task_done()
        self.after(1000, self.checkQueue)

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
            label = ToggleImageLabel(container, images, imageSize, self)
            label.grid(column=column, row=row, sticky=(W))
            self.imageLabels.append(label)

    def addWatch(self, address, callback):
        addr = int(address, 0)
        if addr not in self.addressListeners:
            self.addressListeners[addr] = []
        self.addressListeners[addr].append(callback);

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

    def __init__(self, container, imagelist, size, main):
        ttk.Label.__init__(self, container)
        # we have to keep a copy of every image in this list
        # or it will be garbage collected and not display due to a PIL bug
        self.images = []
        self.currentImage = 0
        self.currentPriority = 0

        self.bind('<ButtonPress>', lambda e: self.switchImage(e))
        for image in imagelist["images"]:
            tkimg = ImageTk.PhotoImage(Image.open(image).resize(size))
            self.images.append(tkimg)
        if "hooks" in imagelist:
            for hook in imagelist["hooks"]:
                self.addHook(hook, main);

        self["image"] = self.images[self.currentImage]

    def addHook(self, hook, main):
        if hook["type"] == "memory":
            self.addMemoryHook(hook, main);

    def addMemoryHook(self, hook, main):
        address = hook["address"]
        value = hook["value"]
        image = hook["image"]
        priority = hook.get("priority", 0)
        main.addWatch(address, lambda d, v=value, i=image, p=priority: self.setImage(v, d, i, p))

    def setImage(self, value, data, image, priority):
        if priority < self.currentPriority:
            return

        if data == value:
            self.currentImage = image
            self.currentPriority = priority
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
        self.currentPriority = 0
        self["image"] = self.images[self.currentImage]


randomizer = RandomizerItems(className="randomizer items")

randomizer.mainloop()

# vim: ai:et:ts=4:sw=4
