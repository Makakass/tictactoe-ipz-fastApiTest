from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import json
import time
import logging
import urllib.request

app = FastAPI()
templates = Jinja2Templates(directory="templates")
logging.basicConfig(level=logging.INFO)
rooms_list = []


def init_board():
    # create empty board
    return [
        None, None, None,
        None, None, None,
        None, None, None,
    ]


def is_draw(board):
    # checks if a draw
    for cell in board:
        if not cell:
            return False
    return True


def if_won(board):
    # check if some player has just won the game
    if board[0] == board[1] == board[2] is not None or \
            board[3] == board[4] == board[5] is not None or \
            board[6] == board[7] == board[8] is not None or \
            board[0] == board[3] == board[6] is not None or \
            board[1] == board[4] == board[7] is not None or \
            board[2] == board[5] == board[8] is not None or \
            board[0] == board[4] == board[8] is not None or \
            board[6] == board[4] == board[2] is not None:
        return True
    return False


@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/create", response_class=HTMLResponse)
async def get_create(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})


@app.post("/create", response_class=RedirectResponse)
async def create(name: str = Form()):
    new_room = Room(name)
    rooms_list.append(new_room)
    logging.info(f'NEW ROOM CREATED: {new_room.room_id}')
    return RedirectResponse('/rooms', status_code=status.HTTP_302_FOUND)


@app.get("/rooms", response_class=HTMLResponse)
async def get_rooms(request: Request):
    # room cleaner + response creator
    data = []
    for room in rooms_list:
        if time.time() - room.create_time >= 60 * 5 and room.conn_manager.connections == []:
            rooms_list.remove(room)
            logging.info(f'ROOM DELETED: {room.room_id}')
            continue
        item = {'id': room.room_id, 'name': room.name}
        data.append(item)
    return templates.TemplateResponse("rooms.html", {"request": request, "data": data})


@app.get("/rooms/{room_id}", response_class=HTMLResponse)
async def get_room(request: Request, room_id: str):
    for room in rooms_list:
        if room.room_id == room_id:
            external_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
            return templates.TemplateResponse("room.html", {"request": request, "data": room_id, "ip": external_ip})
    logging.info('GET to a non-existent room')
    return 'Room does not exist!'


async def update_board(manager, data):
    ind = int(data['cell']) - 1
    data['init'] = False
    if not manager.board[ind]:
        # cell is empty
        manager.board[ind] = data['player']
        if if_won(manager.board):
            data['message'] = "won"
            manager.board = init_board()
        elif is_draw(manager.board):
            data['message'] = "draw"
            manager.board = init_board()
        else:
            data['message'] = "move"
    else:
        data['message'] = "choose another one"
    await manager.broadcast(data)
    if data['message'] in ['draw', 'won']:
        manager.connections = []


class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []
        self.board = init_board()

    async def connect(self, websocket: WebSocket):
        # dealing with incomming connections here
        if len(self.connections) >= 2:
            # denies connection for 3rd player
            await websocket.accept()
            await websocket.close(4000)
        else:
            await websocket.accept()
            # adding the connections to the connection's list
            self.connections.append(websocket)
            if len(self.connections) == 1:
                # the first connected persone plays by X and should wait for a second player
                await websocket.send_json({
                    'init': True,
                    'player': 'X',
                    'message': 'Waiting for another player',
                })
            else:
                # the second player plays by O
                await websocket.send_json({
                    'init': True,
                    'player': 'O',
                    'message': '',
                })
                # signals to the first player that the second player has just connected
                await self.connections[0].send_json({
                    'init': True,
                    'player': 'X',
                    'message': 'Your turn!',
                })

    async def disconnect(self, websocket: WebSocket):
        self.connections.remove(websocket)
        # signal about disconnect and restarting board
        await self.broadcast({
            'init': False,
            'message': 'disconnected',
        })
        self.board = init_board()

    async def broadcast(self, data: dict):
        # broadcasting data to all connected clients
        for connection in self.connections:
            await connection.send_json(data)


class Room:
    def __init__(self, name: str):
        self.room_id = str(id(self))
        self.name = name
        self.create_time = time.time()
        self.conn_manager = ConnectionManager()


@app.websocket("/ws{num}")
async def websocket_endpoint(websocket: WebSocket, num: str):
    # checking for room with this websocket
    manager = None
    for room in rooms_list:
        if room.room_id == num:
            manager = room.conn_manager
            break
    if manager is None:
        logging.info('WS to a non-existent websocket')
        return 'WebSocket does not exist!'
    # connect
    await manager.connect(websocket)
    try:
        while True:
            # here we are waiting for an oncomming message from clients
            data = await websocket.receive_text()
            data = json.loads(data)
            # precessing the incomming message
            await update_board(manager, data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logging.warning(e)
