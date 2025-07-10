import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)

agents = {}
patterns = {}

@app.route('/register_agent', methods=['POST'])
def register_agent():
    data = request.get_json(force=True)
    capabilities = data.get('capabilities', [])
    agent_id = str(uuid.uuid4())
    agents[agent_id] = {'capabilities': capabilities}
    return jsonify({'agent_id': agent_id})

@app.route('/initiate_echo', methods=['POST'])
def initiate_echo():
    data = request.get_json(force=True)
    agent_id = data['agent_id']
    message = data['message']
    if agent_id not in agents:
        return jsonify({'error': 'unknown agent'}), 400
    pattern_id = str(uuid.uuid4())
    patterns[pattern_id] = [{'agent_id': agent_id, 'message': message}]
    return jsonify({'pattern_id': pattern_id})

@app.route('/continue_echo', methods=['POST'])
def continue_echo():
    data = request.get_json(force=True)
    pattern_id = data['pattern_id']
    agent_id = data['agent_id']
    message = data['message']
    if pattern_id not in patterns or agent_id not in agents:
        return jsonify({'error': 'unknown agent or pattern'}), 400
    patterns[pattern_id].append({'agent_id': agent_id, 'message': message})
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
