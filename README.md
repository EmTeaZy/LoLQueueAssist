# League of Legends Auto Queue & Champion Select Tool

A lightweight Python app with a PyQt5 GUI that connects to the League Client’s LCU API using WebSocket to automate queue acceptance, champion banning, and picking.

## Download

Download the latest .exe from [Release](https://github.com/ahtishamdilawar/LoLQueueAssist/releases/latest)

No Python or setup required — just run and go!

## Image
![image](https://github.com/user-attachments/assets/09e99dc4-53be-4951-8135-bfe8bfca987c)


## Features

- Connects to the League Client API using [lcu-driver](https://github.com/sousa-andre/lcu-driver)
- Listens to real-time events from the client (queue pop, champ select, game start)
- Auto-accepts queues immediately
- GUI lets you pick champions to auto-ban and auto-pick
- Plays sound notifications when games start
- Logs key game events for reference
- Minimal RAM and CPU usage, thanks to PyQt5 and efficient threading

## Why use this?

Queue times can be long and frustrating. You often have to sit idle waiting to accept a queue or select champions quickly. This tool speeds up that process so you never miss your queue pop or champion picks.

