#!/usr/bin/python3
# -*- coding: utf-8 -*-

from datetime import datetime, date, timedelta
import flask
from flask import json
import pymysql

VERSION = "1.3.220208"
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "",
    "passwd": "",
    "db": "appstats",
    "charset": "utf8mb4"
}  # TODO
PORT = 5101  # TODO


class Db(object):
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        self.conn = pymysql.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            passwd=DB_CONFIG["passwd"],
            db=DB_CONFIG["db"],
            charset=DB_CONFIG["charset"]
        )
        self.cursor = self.conn.cursor(cursor=pymysql.cursors.DictCursor)

    def log(self, app, pkg, ver, api, api_status,
            os, os_ver, device, device_id, region, ip):
        sql = "INSERT INTO `call` (`app`, `pkg`, `ver`, `api`, `status`," \
              " `os`, `osver`, `device`, `deviceid`, `region`, `ip`)" \
              " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        status = 1
        msg = ""
        try:
            self.cursor.execute(sql, (
                app, pkg, ver, api, api_status,
                os, os_ver, device, device_id, region, ip
            ))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            status = 0
            msg = str(e)
        return status, msg

    def stats(self):
        sql = "SELECT * FROM `stats`"
        res = []
        status = 1
        msg = ""
        try:
            self.cursor.execute(sql, None)
            res = self.cursor.fetchall()
        except Exception as e:
            status = 0
            msg = str(e)
        return res, status, msg

    def fans(self):
        sql = "SELECT * FROM `fans`"
        res = []
        status = 1
        msg = ""
        try:
            self.cursor.execute(sql, None)
            res = self.cursor.fetchone()
        except Exception as e:
            status = 0
            msg = str(e)
        return res, status, msg

    def beat(self):
        sql = "SELECT * FROM `beat`"
        res = []
        status = 1
        msg = ""
        try:
            self.cursor.execute(sql, None)
            res = self.cursor.fetchall()
        except Exception as e:
            status = 0
            msg = str(e)
        return res, status, msg

    def close(self):
        self.cursor.close()
        self.conn.close()


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, obj)


server = flask.Flask(__name__)
# 解决日期转换问题
server.json_encoder = ComplexEncoder


@server.route("/", methods=["GET", "POST"])
def homepage():
    return flask.redirect("/appstats/timeline", code=302)
    # or return flask.redirect(flask.url_for("timeline"), code=302)


@server.route("/appstats/timeline", methods=["GET", "POST"])
def timeline():
    with Db() as db:
        data_stats = db.stats()
        data_fans = db.fans()
        data_beath = db.beat()
    if data_stats[1] != 1:
        return flask.render_template("appstats.html")
    data_stats = data_stats[0]
    data_stats.sort(key=lambda d: (
        d["date"].strftime("%Y%m%d") if d["date"] else ""
    ), reverse=True)  # 按日期降序，汇总列最后
    data_today = data_stats[0]
    data_sum = data_stats[len(data_stats) - 1]
    data_out = {
        "debug": "ubuntu 20.04"
                 " | mysql 8.0.27"
                 " | python 3.8.10"
                 " | flask 2.0.2"
                 " | nginx 1.18.0"
                 " | server %s" % ".".join(str(PORT)),
        "beath": {},
        "beatd": {
            "label": [],
            "data1": [],
            "data2": []
        },
        "user": {
            "label": [],
            "data1": [],
            "data2": []
        },
        "api": {
            "label": ["Bing", "NASA", "OnePlus", "拾光", "向日葵8号",
                      "一梦幽黎", "Infinity", "其他"],
            "data1": [data_sum["/bing"], data_sum["/nasa"],
                      data_sum["/oneplus"], data_sum["/timeline"],
                      data_sum["/himawari8"], data_sum["/ymyouli"],
                      data_sum["/infinity"], data_sum["/other"]],
            "data2": [data_today["/bing"], data_today["/nasa"],
                      data_today["/oneplus"], data_today["/timeline"],
                      data_today["/himawari8"], data_today["/ymyouli"],
                      data_today["/infinity"], data_today["/other"]]
        },
        "region": {
            "label": ["中国大陆", "美国", "中国香港", "印度", "英国", "巴西", "土耳其", "其他"],
            "data1": [data_sum["cn"], data_sum["us"],
                      data_sum["hk"], data_sum["in"],
                      data_sum["gb"], data_sum["br"],
                      data_sum["tr"], data_sum["other"]],
            "data2": [data_today["cn"], data_today["us"],
                      data_today["hk"], data_today["in"],
                      data_today["gb"], data_today["br"],
                      data_today["tr"], data_today["other"]]
        },
        "src": {
            "label": ["商店", "其他"],
            "data1": [data_sum["store"]],
            "data2": [data_today["store"]]
        },
        "ver": {
            "label": ["新版本", "老版本"],
            "data1": [data_sum["newver"]],
            "data2": [data_today["newver"]]
        },
        "os": {
            "label": ["Win11", "Win10"],
            "data1": [data_sum["win11"]],
            "data2": [data_today["win11"]]
        },
        "fan": {
            "label": ["1天+", "2天+", "5天+", "7天+", "14天+", "21天+", "28天+"]
        }
    }
    if data_beath[1] == 1:
        data_beat = data_beath[0]
        data_beat.sort(key=lambda d: d["hour"])
        data_out["beath"]["label"] = ["%s/%s %s:00" % (
            item["hour"][4:6], item["hour"][6:8], item["hour"][8:]
        ) for item in data_beat]
        data_out["beath"]["data1"] = [-item["total"] for item in data_beat]
        data_out["beath"]["data2"] = [item["devices"] for item in data_beat]
    for item in data_stats[:(77 if len(data_stats) - 1 >= 77 else -1)]:
        # 跳过汇总，取161天
        data_out["beatd"]["label"].insert(0, item["date"].strftime("%m/%d"))
        data_out["beatd"]["data1"].insert(0, -item["total"])
        data_out["beatd"]["data2"].insert(0, item["devices"])
    for i in range(77 - (len(data_stats) - 1)):
        data_out["beatd"]["label"].insert(0, (
            data_stats[-2]["date"] + timedelta(days=-(i + 1))
        ).strftime("%m/%d"))
        data_out["beatd"]["data1"].insert(0, 0)
        data_out["beatd"]["data2"].insert(0, 0)
    for i in range(7):
        data_out["beatd"]["label"].append((
            data_stats[0]["date"] + timedelta(days=(i + 1))
        ).strftime("%m/%d"))
        data_out["beatd"]["data1"].append(0)
        data_out["beatd"]["data2"].append(0)
    for item in data_stats[:(7 if len(data_stats) >= 8 else -1)]:
        # 跳过汇总，取一周
        # data_out["user"]["label"].insert(0, (
        #     "周一", "周二", "周三", "周四", "周五", "周六", "周日"
        # )[item["date"].weekday()])
        data_out["user"]["label"].insert(0, item["date"].strftime("%m/%d"))
        # data_out["user"]["data1"].insert(0, item["total"])
        data_out["user"]["data1"].insert(0, item["newcomers"])
        data_out["user"]["data2"].insert(0, item["devices"] - item["newcomers"])
    data_out["src"]["data1"].append(
        data_sum["devices"] - sum(data_out["src"]["data1"])
    )
    data_out["src"]["data2"].append(
        data_today["devices"] - sum(data_out["src"]["data2"])
    )
    data_out["ver"]["data1"].append(
        data_sum["devices"] - sum(data_out["ver"]["data1"])
    )
    data_out["ver"]["data2"].append(
        data_today["devices"] - sum(data_out["ver"]["data2"])
    )
    data_out["os"]["data1"].append(
        data_sum["devices"] - sum(data_out["os"]["data1"])
    )
    data_out["os"]["data2"].append(
        data_today["devices"] - sum(data_out["os"]["data2"])
    )
    if data_fans[1] == 1:
        data_fans = data_fans[0]
        data_out["fan"]["data1"] = [
            data_fans["d1"], data_fans["d2"], data_fans["d3"], data_fans["d4"],
            data_fans["d5"], data_fans["d6"], data_fans["d7"]
        ]
    return flask.render_template("appstats.html", **data_out)


@server.route("/appstats", methods=["GET", "POST"])
def appstats():
    if flask.request.method != "POST":
        return flask.redirect("/appstats/timeline", code=302)
    if not flask.request.data:
        return flask.jsonify({
            "status": 0,
            "msg": "invalid method or params"
        })
    data = flask.json.loads(flask.request.data.decode("utf-8"))
    app = data.get("app")
    pkg = data.get("pkg")
    ver = data.get("ver")
    api = data.get("api")
    api_status = data.get("status")
    os = data.get("os")
    os_ver = data.get("osver")
    device = data.get("device")
    device_id = data.get("deviceid")
    region = data.get("region")
    if (not app and not pkg and not ver and not api and not api_status
            and not os and not os_ver and not device and not device_id
            and not region):
        return flask.jsonify({
            "status": 0,
            "msg": "invalid params"
        })
    # ip = flask.request.remote_addr # 使用 Nginx 反向代理后结果为 127.0.0.1
    # proxy_set_header Host $host;
    # proxy_set_header X-Real-IP $remote_addr;
    # proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    ip = flask.request.headers.get("X-Forwarded-For",
                                   flask.request.remote_addr)
    with Db() as db:
        res = db.log(app, pkg, ver, api, api_status,
                     os, os_ver, device, device_id, region, ip)
    return flask.jsonify({
        "status": res[0],
        "msg": res[1]
    })


if __name__ == "__main__":
    server.run(debug=False, port=PORT, host="localhost")
    # server.run(debug=False, port=80, host="0.0.0.0")
    # server.run(debug=False, port=443, host="0.0.0.0", ssl_context=(
    #     "cert/1_api.nguaduot.cn_bundle.crt",
    #     "cert/2_api.nguaduot.cn.key"
    # ))
