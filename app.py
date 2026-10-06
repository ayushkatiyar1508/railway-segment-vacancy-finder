from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

TRAINS = [{
    "number": "12345", "name": "Example Express", "source": "NDLS", "destination": "LKO",
    "stations": [
        {"code":"NDLS","name":"New Delhi","day":1,"arr":"06:00","dep":"06:20"},
        {"code":"GZB","name":"Ghaziabad","day":1,"arr":"07:05","dep":"07:10"},
        {"code":"ALJN","name":"Aligarh Jn","day":1,"arr":"08:20","dep":"08:25"},
        {"code":"CNB","name":"Kanpur Central","day":1,"arr":"12:30","dep":"12:40"},
        {"code":"LKO","name":"Lucknow","day":1,"arr":"14:15","dep":"14:25"}
    ]
}]

DEMO_BOOKINGS = [
    {"coach":"B1","berth":"21","from":"NDLS","to":"ALJN"},
    {"coach":"B1","berth":"22","from":"CNB","to":"LKO"},
    {"coach":"B2","berth":"36","from":"NDLS","to":"ALJN"},
    {"coach":"B2","berth":"40","from":"GZB","to":"CNB"}
]

def train_between(source, destination):
    source, destination = source.upper(), destination.upper()
    return [t for t in TRAINS
            if source in [s["code"] for s in t["stations"]]
            and destination in [s["code"] for s in t["stations"]]
            and [s["code"] for s in t["stations"]].index(source)
                < [s["code"] for s in t["stations"]].index(destination)]

def segment_vacancy(train, source, destination):
    codes = [s["code"] for s in train["stations"]]
    si, di = codes.index(source), codes.index(destination)
    route = codes[si:di+1]
    inventory = [{"coach":c,"berth":str(b),"bookings":[]}
                 for c in ("B1","B2","B3") for b in range(1,9)]
    for seat in inventory:
        seat["bookings"] = [x for x in DEMO_BOOKINGS
                            if x["coach"]==seat["coach"] and x["berth"]==seat["berth"]]
    result=[]
    for seat in inventory:
        overlap=False
        for b in seat["bookings"]:
            if b["from"] in route and b["to"] in route:
                a,z=route.index(b["from"]),route.index(b["to"])
                if a < z and a < len(route)-1 and z > 0:
                    overlap=True
        if not overlap:
            result.append({"coach":seat["coach"],"berth":seat["berth"],
                           "status":"VACANT","from":source,"to":destination})
    return result

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/trains")
def api_trains():
    source=request.args.get("source","").strip()
    destination=request.args.get("destination","").strip()
    if not source or not destination:
        return jsonify({"error":"source and destination are required"}),400
    return jsonify({"trains":train_between(source,destination)})

@app.get("/api/train/<number>")
def api_train(number):
    train=next((t for t in TRAINS if t["number"]==number),None)
    if not train: return jsonify({"error":"Train not found in demo data"}),404
    return jsonify(train)

@app.get("/api/vacancy")
def api_vacancy():
    number=request.args.get("train")
    source=request.args.get("source","").upper()
    destination=request.args.get("destination","").upper()
    train=next((t for t in TRAINS if t["number"]==number),None)
    if not train: return jsonify({"error":"Train not found"}),404
    codes=[s["code"] for s in train["stations"]]
    if source not in codes or destination not in codes or codes.index(source)>=codes.index(destination):
        return jsonify({"error":"Invalid route segment"}),400
    return jsonify({"train":{"number":train["number"],"name":train["name"]},
                     "source":source,"destination":destination,
                     "vacant_berths":segment_vacancy(train,source,destination),
                     "data_mode":"DEMO"})

@app.get("/api/status/<number>")
def api_status(number):
    return jsonify({"train":number,"status":"LIVE_PROVIDER_NOT_CONNECTED",
                    "message":"Connect an authorized/contracted train-running-status provider here."})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000,debug=True)
