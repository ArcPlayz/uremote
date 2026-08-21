from aiohttp import web

from itertools import batched
from collections import namedtuple

from evdev import UInput, AbsInfo
from evdev.ecodes import ecodes as e

from argparse import ArgumentParser

async def handle_index(request):
    return web.Response(
        text = open('app.html').read() if request.remote != '127.0.0.1' else 'You should open this page on your phone instead.',
        content_type = 'text/html'
    )

Touch = namedtuple('Touch', ('slot', 'x', 'y'))

TP_EVENTS = (e['BTN_TOOL_FINGER'], e['BTN_TOOL_DOUBLETAP'], e['BTN_TOOL_TRIPLETAP'], e['BTN_TOOL_QUADTAP'])

kb = None
tp = None
buttons = None
touches = 0

async def handle_init(request):
    global buttons, touches, kb, tp

    buttons = tuple(e[b] for b in await request.json())

    touches = 0

    if kb: kb.close()
    if tp: tp.close()

    kb = UInput({
        e['EV_KEY']: buttons,
    }, 'uremote-kb')
    tp = UInput({
        e['EV_KEY']: (e['BTN_TOUCH'], *TP_EVENTS),
        e['EV_ABS']: (
            (e['ABS_MT_SLOT'], AbsInfo(0, 0, 3, 0, 0, 0)),
            (e['ABS_MT_TRACKING_ID'], AbsInfo(0, 0, 3, 0, 0, 0)),
            (e['ABS_MT_POSITION_X'], AbsInfo(0, 0, 2047, 0, 0, 0)),
            (e['ABS_MT_POSITION_Y'], AbsInfo(0, 0, 2047, 0, 0, 0))
        )
    }, 'uremote-tp')

    return web.Response(status = 200)

async def handle_websocket(request):
    sock = web.WebSocketResponse()
    await sock.prepare(request)

    print(f'{request.remote} connected!')
    
    global touches

    async for msg in sock:
        t = msg.data[0]
        p = msg.data[1:]
        if t in (0, 1):
            kb.write(e['EV_KEY'], buttons[p[0]], not t)
            kb.syn()
        elif t in (2, 3, 4):
            _touches = tuple(
                Touch(
                    (_p := int.from_bytes(__p, 'little')) & 3,
                    _p >> 2 & 2047,
                    _p >> 13
                ) for __p in batched(p, 3 if t != 4 else 1)
            )

            if t != 3:
                if not touches:
                    tp.write(e['EV_KEY'], e['BTN_TOUCH'], 1)

                touches += len(_touches) * (1 if t == 2 else -1)

                if not touches:
                    tp.write(e['EV_KEY'], e['BTN_TOUCH'], 0)

                for i, ev in enumerate(TP_EVENTS):
                    tp.write(e['EV_KEY'], ev, 0 if i + 1 != touches else 1)

            for touch in _touches:
                tp.write(e['EV_ABS'], e['ABS_MT_SLOT'], touch.slot)

                if t != 3:
                    tp.write(e['EV_ABS'], e['ABS_MT_TRACKING_ID'], touch.slot if t == 2 else -1)

                if t != 4:
                    tp.write(e['EV_ABS'], e['ABS_MT_POSITION_X'], touch.x)
                    tp.write(e['EV_ABS'], e['ABS_MT_POSITION_Y'], touch.y)

            tp.syn()

    return sock

app = web.Application()
app.router.add_get('/', handle_index)
app.router.add_get('/ws', handle_websocket)
app.router.add_post('/init', handle_init)

if __name__ == '__main__':
    parser = ArgumentParser('uremote')

    parser.add_argument(
        '--host', default = '0.0.0.0', type = str, help = 'ip address the server is listening on'
    )
    parser.add_argument(
        '--port', default = 7777, type = int, help = 'port the server is listening on'
    )
    
    args = parser.parse_args()

    web.run_app(app, host = args.host, port = args.port)
