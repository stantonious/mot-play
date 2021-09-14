import json
from pymaze.maze_manager import MazeManager
from pymaze import encoder
import time

NORTH_BIT = 0x0001
SOUTH_BIT = 0x0002
EAST_BIT = 0x0004
WEST_BIT = 0x0008

err = ''


def get_from_id(_id):
    try:
        with open(f'/mnt/mot/{_id}.json', 'r') as f:
            return json.loads(f.read())
    except Exception as e:
        print(e)
        err = f'failed to load {_id}'
        return None


def save_data(d):
    with open(f'/mnt/mot/{d["id"]}.json', 'w') as f:
        f.write(json.dumps(d))


def lambda_handler(event, context):
    id = int(time.time())
    maze_x = int(event["queryStringParameters"]['x'] if 'x' in event["queryStringParameters"] else 0)
    maze_y = int(event["queryStringParameters"]['y'] if 'y' in event["queryStringParameters"] else 0)
    maze_id = int(event["queryStringParameters"]['id'] if 'id' in event["queryStringParameters"] else 0)

    result = None

    if maze_x != 0 and maze_y != 0:

        manager = MazeManager()
        maze = manager.add_maze(int(maze_x), int(maze_y))
        data = encoder.encode(maze.grid)

        # Add high/low walls
        for _s,_i in enumerate(range(0, maze_x, 2)):
            if data[_i][_i] & encoder.NORTH_BIT:
                encoder.add_status(data, _i, _i, encoder.NORTH_BIT, (_s % 2) + 2)
            elif data[_i][_i] & encoder.SOUTH_BIT:
                encoder.add_status(data, _i, _i, encoder.SOUTH_BIT, (_s % 2) + 2)
            elif data[_i][_i] & encoder.EAST_BIT:
                encoder.add_status(data, _i, _i, encoder.EAST_BIT, (_s % 2) + 2)
            elif data[_i][_i] & encoder.WEST_BIT:
                encoder.add_status(data, _i, _i, encoder.WEST_BIT, (_s % 2) + 2)

        result = {'Name': 'foo',
                  'id': f'{id}',
                  'shape': [maze_x, maze_y],
                  'entry' : maze.entry_coor,
                  'exit' : maze.exit_coor,
                  'cells': data}

        save_data(result);

    elif maze_id != 0:
        result = get_from_id(maze_id)
        print(f' got result {json.dumps(result)}')

    if result:
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    else:
        return {
            'statusCode': 400,
            'body': err}
