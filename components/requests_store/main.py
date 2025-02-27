from flask import Flask, jsonify
from flask import request
from flask_cors import CORS
import argparse
import logging
import requests
from models.req import Req
from models.model import Model
from models.container import Container
from configuration import RequestsStoreConfiguration

app = Flask(__name__)
CORS(app)

status = None
reqs = {}
config = None
models = []
containers = []


@app.route('/', methods=['GET'])
def get_status():
    return {"status": status}


@app.route('/requests', methods=['DELETE'])
def delete_requests():
    global reqs
    reqs = {}
    return jsonify(reqs)


@app.route('/requests', methods=['GET', 'POST'])
def get_requests():
    if request.method == 'GET':
        verbose = request.args.get('verbose')
        reqs_list = list(reqs.values())
        if verbose is None or int(verbose) == 0:
            return jsonify([req.to_json(verbose=False) for req in reqs_list])
        else:
            return jsonify([req.to_json(verbose=True) for req in reqs_list])
    elif request.method == 'POST':
        rs = request.get_json()
        reqs[rs["id"]] = Req(json_data=rs)
        # app.logger.info("+ %s", rs)
        return jsonify(rs)


@app.route('/requests/<node>', methods=['GET'])
def get_requests_by_node(node):
    reqs_list = list(reqs.values())
    return jsonify([req.to_json() for req in list(filter(lambda r: r.node == node, reqs_list))])


@app.route('/metrics/model', methods=['GET'])
def get_metrics_by_model():
    metrics = []
    from_ts = request.args.get('from_ts')

    for model in models:
        # filter the reqs associated with the model
        reqs_list = list(reqs.values())
        model_reqs = list(filter(lambda r: r.model == model.name and r.version == model.version, reqs_list))
        if from_ts is not None:
            # compute the metrics from ts
            metrics.append(
                {"model": model.name,
                 "version": model.version,
                 "metrics_from_ts": Req.metrics(model_reqs, from_ts)})
        else:
            # compute the metrics
            metrics.append(
                {"model": model.name,
                 "version": model.version,
                 "metrics": Req.metrics(model_reqs)})
    return jsonify(metrics)


@app.route('/metrics/container', methods=['GET'])
def get_metrics_by_container():
    metrics = []
    from_ts = request.args.get('from_ts')

    for container in containers:
        # filter the reqs associated with the container
        reqs_list = list(reqs.values())
        container_reqs = list(filter(lambda r: r.container_id == container.container_id, reqs_list))

        if from_ts is not None:
            # compute the metrics from ts
            metrics.append({"container": container.to_json(),
                            "metrics_from_ts": Req.metrics(container_reqs, from_ts)})
        else:
            # compute the metrics
            metrics.append({"container": container.to_json(),
                            "metrics": Req.metrics(container_reqs)})
    return jsonify(metrics)


@app.route('/metrics/container/model', methods=['GET'])
def get_metrics_by_container_model():
    metrics = {}
    from_ts = request.args.get('from_ts')
    if from_ts is None:
        from_ts = 0
    else:
        from_ts = float(from_ts)

    for container in containers:
        # filter the reqs associated with the container
        reqs_list = list(reqs.values())
        container_reqs = list(filter(lambda r: r.container_id == container.container_id, reqs_list))

        reqs_by_model = {}
        for model in models:
            reqs_model = list(filter(lambda r: r.model == model.name, container_reqs))
            reqs_metrics = Req.metrics(reqs_model, from_ts)
            reqs_by_model[model.name] = reqs_metrics

        # compute the metrics
        metrics[container.container_id] = reqs_by_model
    return jsonify(metrics)


def get_data(url):
    try:
        response = requests.get(url)
    except Exception as e:
        logging.warning(e)
        response = []
    print(response)
    return response.json()


"""
@app.route('/metrics/model/<model>/<version>', methods=['GET'])
def get_metrics_by_model_interval(model, version):
    metrics = []
    model = str(model)
    version = int(version)
    samples_size = 30
    samples_width = 1
    start_ts = time.time() - samples_size*samples_width
    end_ts = start_ts + samples_width

    for interval in range(samples_size):
        # filter the reqs associated with the model
        model_reqs_interval = list(filter(lambda r: r.model == model and
                                                    r.version == version and
                                                    start_ts < r.ts_in < end_ts, reqs.values()))

        # compute the metrics
        metrics.append(
            {"interval": interval,
             "metrics": Req.metrics(model_reqs_interval)})

        start_ts = start_ts + samples_width
        end_ts = start_ts + samples_width

    return jsonify(intervals=metrics)
"""


@app.route('/configuration', methods=['GET'])
def get_configuration():
    logging.info("get configuration")
    if config:
        return {"configuration": config.__dict__}, 200
    else:
        logging.warning("configuration not found")
        return {"configuration": "not found"}, 400


@app.route('/configuration', methods=['POST'])
def configure():
    global status, config

    logging.info("configuration started...")

    # read data
    data = request.get_json()
    config = RequestsStoreConfiguration(json_data=data)

    logging.info("Getting models from: %s", config.models_endpoint)
    logging.info("Getting containers from: %s", config.containers_endpoint)

    status = "configured"
    logging.info(status)

    return {"result": "ok"}, 200


@app.route('/start', methods=['POST'])
def start_requests_store():
    global status, config, models, containers

    # get models information
    models = [Model(json_data=json_model) for json_model in get_data(config.models_endpoint)]
    logging.info("Models: %s", [model.to_json() for model in models])

    # get containers information
    containers = [Container(json_data=json_container) for json_container in get_data(config.containers_endpoint)]
    logging.info("Containers: %s", [container.to_json() for container in containers])

    status = "active"
    logging.info(status)

    return {"result": "ok"}, 200


if __name__ == "__main__":
    # init log
    log_format = "%(asctime)s:%(levelname)s:%(name)s:" \
                 "%(filename)s:%(lineno)d:%(message)s"
    logging.basicConfig(level='DEBUG', format=log_format)

    status = "inactive"
    logging.info(status)

    app.run(host='0.0.0.0', port=5002)
