from flask import Flask, request, jsonify

app = Flask(__name__)

# Глобальное состояние сервера
last_input = None
last_task = None
task_result_sent = False

@app.route('/inputs', methods=['POST'])
def handle_inputs():
    global last_input
    data = request.json
    
    if not data or 'view' not in data or not isinstance(data['view'], list):
        return jsonify({"action": "None"}), 400
    
    # Проверка вложенной структуры
    for row in data['view']:
        if not isinstance(row, list) or not all(isinstance(x, int) for x in row):
            return jsonify({"action": "None"}), 400
    
    last_input = data['view']
    return jsonify({"action": "processed"}), 200

@app.route('/tasks', methods=['POST'])
def handle_tasks():
    global last_task, task_result_sent
    data = request.json
    
    if not data or 'type' not in data or 'task' not in data:
        return "", 400
    
    # Сбрасываем флаг отправки результата для новой задачи
    task_result_sent = False
    last_task = {
        "type": data['type'],
        "task": data['task']
    }
    
    answer = "Да"  

    return jsonify({"answer": answer}), 200

@app.route('/tasks/last', methods=['PATCH'])
def handle_last_task():
    global task_result_sent
    data = request.json
    
    if not data or 'result' not in data or data['result'] not in ["Ok", "TryAgain", "Fail"]:
        return "", 400
    
    # Проверка наличия задачи
    if last_task is None or task_result_sent:
        return "", 404
    
    task_result_sent = True
    return "", 200

@app.route('/notifications', methods=['POST'])
def handle_notifications():
    data = request.json
    
    # Проверка формата
    if not data or 'type' not in data or 'desc' not in data:
        return "", 400
    
    return "", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)