Provides access to a com-port device via REST and WebSockets.

To quickly test this on Linux:

- create a virtual com-port attached over USB, *socat* will run as a background job:

```bash
nohup sudo socat -d -d pty,raw,echo=0,link=/dev/ttyUSB100 pty,raw,echo=0,link=./local_com &
awk '/PTY is/ {a_prev=a; a=$NF} END{cmd="for i in " a_prev " " a "; do sudo chmod +777 $i; done"; system(cmd)}' nohup.out
```

- connect to it. Use *C-a C-c* to turn local echo on, *C-a C-q* to exit:

```bash
picocom ./local_com
```

- prepare *virtualenv* and activate it:

```bash
python3.8 -m virtualenv venv
. venv/bin/activate
pip install -r requirements.txt
```

- run the server like this:

```bash
venv/bin/hypercorn serious_quartz:app --error-log - --access-log -
```

- connect with a WebSocket client:

```bash
wscat -c localhost:8000/api
```

- type and send something in *picocom*:

<div float="left">
    <img src="assets/picocom.png" />
    [![youtube link](https://img.youtube.com/vi/Q7wuADjRx10/0.jpg)](https://www.youtube.com/watch?v=Q7wuADjRx10)
</div>


- shut *socat* down:

```bash
a=$(jobs | awk -F'[][]' '/local_com/ {system("echo fg %"$2)}')
$a
```
