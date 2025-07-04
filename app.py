from flask import Flask, request, redirect, render_template_string, send_file, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from config import MONGO_URI, DB_NAME, COLLECTION_NAME, USERS_COLLECTION_NAME
from login_system import register_routes, protect
import csv
import io

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Setup MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
users_collection = db[USERS_COLLECTION_NAME]

register_routes(app, users_collection)

HTML_TEMPLATE = """
<!doctype html>
<html lang=\"en\">
<head>
    <meta charset="UTF-8">
  <title>Jurnal Trading</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" type="image/png" href="https://i.pinimg.com/736x/37/c4/45/37c4456556677bfdeae77827fcd9bb58.jpg">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet">
  <link href="https://cdn.datatables.net/1.13.5/css/dataTables.bootstrap5.min.css" rel="stylesheet">
  <style>
    body.dark { background-color: #121212 !important; color: #f0f0f0; }
    .dark .table, .dark .form-control, .dark .btn { background-color: #333 !important; color: #fff; border-color: #555; }
    .dark .card { background-color: #1e1e1e; border-color: #444; }
    .dark .card-title, .dark .card-text { color: #f0f0f0 !important; }
    .dark .dataTables_wrapper,
    .dark .dataTables_filter input,
    .dark .dataTables_length select,
    .dark .paginate_button,
    .dark .table-striped > tbody > tr:nth-of-type(odd) {
      background-color: #1e1e1e !important;
      color: #f0f0f0 !important;
      border-color: #444 !important;
    }
    .dark .paginate_button.current {
      background-color: #444 !important;
      color: #fff !important;
    }
    .result-tp { color: limegreen; font-weight: bold; }
    .result-sl { color: red; font-weight: bold; }
    .theme-toggle { position: fixed; top: 1rem; right: 1rem; cursor: pointer; }
    @media (max-width: 768px) {
      .table-responsive { overflow-x: auto; }
    }
  </style>
</head>
<body class=\"bg-light p-4\" id=\"body\">
  <div class=\"theme-toggle\">
    <button class=\"btn btn-outline-secondary\" onclick=\"toggleTheme()\">🌙☀️</button>
  </div>
  <div class=\"container\">
    <div class=\"d-flex justify-content-end\">
      <a href=\"/logout\" class=\"btn btn-outline-danger mb-3\">Logout ({{ session['username'] }})</a>
    </div>
    <h2 class=\"text-center mb-4\">Jurnal Trading XAUUSD</h2>
    {% if edit_data %}
    <form method=\"POST\" action=\"/edit/{{ edit_data._id }}\" class=\"mb-5\">
    {% else %}
    <form method=\"POST\" class=\"mb-5\" onsubmit=\"return confirm('Yakin data sudah benar?')\">
    {% endif %}
      <div class=\"row g-3\">
        <div class=\"col-md-4\">
          <label>Equity Awal ($)</label>
          <input type=\"number\" step=\"0.01\" name=\"equity\" class=\"form-control\" value=\"{{ edit_data.equity if edit_data else '' }}\" required>
        </div>
        <div class=\"col-md-4\">
          <label>Lot Size</label>
          <input type=\"number\" step=\"0.01\" min=\"0.01\" name=\"lot\" class=\"form-control\" value=\"{{ edit_data.lot if edit_data else '' }}\" required>
        </div>
        <div class=\"col-md-4\">
          <label>Open Price</label>
          <input type=\"number\" step=\"0.001\" name=\"open_price\" class=\"form-control\" value=\"{{ edit_data.open_price if edit_data else '' }}\" required>
        </div>
        <div class=\"col-md-4\">
          <label>Stop Loss</label>
          <input type=\"number\" step=\"0.001\" name=\"sl\" class=\"form-control\" value=\"{{ edit_data.sl if edit_data else '' }}\" required>
        </div>
        <div class=\"col-md-4\">
          <label>Take Profit</label>
          <input type=\"number\" step=\"0.001\" name=\"tp\" class=\"form-control\" value=\"{{ edit_data.tp if edit_data else '' }}\" required>
        </div>
        <div class=\"col-md-4\">
          <label>Hasil</label>
          <select name=\"result\" class=\"form-control\" required>
            <option value=\"TP\" {% if edit_data and edit_data.result == 'TP' %}selected{% endif %}>✔️ TP</option>
            <option value=\"SL\" {% if edit_data and edit_data.result == 'SL' %}selected{% endif %}>❌ SL</option>
          </select>
        </div>
        <div class=\"col-md-12\">
          <label>Keterangan</label>
          <select name=\"note\" class=\"form-control\">
            <option value=\"Buy\" {% if edit_data and edit_data.note == 'Buy' %}selected{% endif %}>Buy</option>
            <option value=\"Sell\" {% if edit_data and edit_data.note == 'Sell' %}selected{% endif %}>Sell</option>
          </select>
        </div>
      </div>
      <button type=\"submit\" class=\"btn btn-primary mt-4\">{{ 'Update' if edit_data else 'Simpan' }}</button>
      <a href=\"/export\" class=\"btn btn-success mt-4 ms-2\">Export CSV</a>
    </form>

    <div class=\"row mb-4\">
      <div class=\"col-md-3\">
        <div class=\"card text-center\">
          <div class=\"card-body\">
            <h5 class=\"card-title\">Total Trades</h5>
            <p class=\"card-text fs-4\">{{ stats.total }}</p>
          </div>
        </div>
      </div>
      <div class=\"col-md-3\">
        <div class=\"card text-center\">
          <div class=\"card-body\">
            <h5 class=\"card-title\">Total TP</h5>
            <p class=\"card-text fs-4 text-success\">{{ stats.tp }}</p>
          </div>
        </div>
      </div>
      <div class=\"col-md-3\">
        <div class=\"card text-center\">
          <div class=\"card-body\">
            <h5 class=\"card-title\">Total SL</h5>
            <p class=\"card-text fs-4 text-danger\">{{ stats.sl }}</p>
          </div>
        </div>
      </div>
      <div class=\"col-md-3\">
        <div class=\"card text-center\">
          <div class=\"card-body\">
            <h5 class=\"card-title\">Winrate</h5>
            <p class=\"card-text fs-4\">{{ stats.winrate }}%</p>
          </div>
        </div>
      </div>
    </div>

    <div class=\"table-responsive\">
      <table id=\"tradeTable\" class=\"table table-bordered table-striped shadow-sm\">
        <thead>
          <tr>
            <th>Action</th>
            <th>No</th>
            <th>Tanggal & Waktu</th>
            <th>Equity Awal</th>
            <th>Lot</th>
            <th>Open Price</th>
            <th>SL</th>
            <th>TP</th>
            <th>Hasil</th>
            <th>Keterangan</th>
            <th>Profit</th>
            <th>Equity After</th>
          </tr>
        </thead>
        <tbody>
          {% for trade in trades %}
          <tr>
            <td>
              <a href=\"/edit/{{ trade._id }}\" class=\"btn btn-sm btn-warning\"><i class=\"bi bi-pencil-square\"></i></a>
              <a href=\"/delete/{{ trade._id }}\" class=\"btn btn-sm btn-danger\" onclick=\"return confirm('Yakin mau hapus data ini?')\"><i class=\"bi bi-trash\"></i></a>
            </td>
            <td>{{ loop.index }}</td>
            <td>{{ trade.date }}</td>
            <td>${{ '%.2f'|format(trade.equity) }}</td>
            <td>{{ trade.lot }}</td>
            <td>{{ trade.open_price }}</td>
            <td>{{ trade.sl }}</td>
            <td>{{ trade.tp }}</td>
            <td class=\"{{ 'result-tp' if trade.result == 'TP' else 'result-sl' }}\">{{ trade.result }}</td>
            <td>{{ trade.note }}</td>
            <td>${{ '%.2f'|format(trade.equity_after - trade.equity) }}</td>
            <td>${{ '%.2f'|format(trade.equity_after) }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  <script src=\"https://code.jquery.com/jquery-3.7.0.min.js\"></script>
  <script src=\"https://cdn.datatables.net/1.13.5/js/jquery.dataTables.min.js\"></script>
  <script src=\"https://cdn.datatables.net/1.13.5/js/dataTables.bootstrap5.min.js\"></script>
  <script>
    $(document).ready(function() {
      $('#tradeTable').DataTable();
    });
    function toggleTheme() {
      const body = document.getElementById('body');
      const dark = body.classList.toggle('dark');
      localStorage.setItem('theme', dark ? 'dark' : 'light');
      document.querySelectorAll('.dataTables_wrapper').forEach(e => {
        if (dark) e.classList.add('dark');
        else e.classList.remove('dark');
      });
    }
    window.onload = () => {
      if (localStorage.getItem('theme') === 'dark') {
        document.getElementById('body').classList.add('dark');
        setTimeout(() => {
          document.querySelectorAll('.dataTables_wrapper').forEach(e => e.classList.add('dark'));
        }, 100);
      }
    }
  </script>
</body>
</html>
"""
@app.route('/', methods=['GET', 'POST'])
def index():
    check = protect()
    if check: return check

    username = session["username"]

    if request.method == 'POST':
        equity = float(request.form['equity'])
        lot = float(request.form['lot'])
        open_price = float(request.form['open_price'])
        sl = float(request.form['sl'])
        tp = float(request.form['tp'])
        result = request.form['result']
        note = request.form['note']
        pip_value = 100 * lot

        if note == 'Buy':
            pnl = (tp - open_price) * pip_value if result == 'TP' else (sl - open_price) * pip_value
        else:
            pnl = (open_price - tp) * pip_value if result == 'TP' else (sl - open_price) * pip_value * -1

        equity_after = equity + pnl

        trade = {
            "username": username,
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "equity": equity,
            "lot": lot,
            "open_price": open_price,
            "sl": sl,
            "tp": tp,
            "result": result,
            "note": note,
            "equity_after": equity_after
        }

        collection.insert_one(trade)
        return redirect('/')

    trades = list(collection.find({"username": username}).sort("date", -1))
    tp_count = sum(1 for t in trades if t['result'] == 'TP')
    sl_count = sum(1 for t in trades if t['result'] == 'SL')
    total = len(trades)
    start_equity = trades[-1]['equity'] if trades else 0
    end_equity = trades[0]['equity_after'] if trades else 0
    winrate = round((tp_count / total) * 100, 2) if total else 0

    stats = {
        "tp": tp_count,
        "sl": sl_count,
        "total": total,
        "winrate": winrate,
        "growth": end_equity - start_equity
    }

    return render_template_string(HTML_TEMPLATE, trades=trades, stats=stats, edit_data=None)

@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    check = protect()
    if check: return check

    username = session["username"]

    if request.method == 'POST':
        equity = float(request.form['equity'])
        lot = float(request.form['lot'])
        open_price = float(request.form['open_price'])
        sl = float(request.form['sl'])
        tp = float(request.form['tp'])
        result = request.form['result']
        note = request.form['note']
        pip_value = 100 * lot

        if note == 'Buy':
            pnl = (tp - open_price) * pip_value if result == 'TP' else (sl - open_price) * pip_value
        else:
            pnl = (open_price - tp) * pip_value if result == 'TP' else (sl - open_price) * pip_value * -1

        equity_after = equity + pnl

        collection.update_one(
            {"_id": ObjectId(id), "username": username},
            {"$set": {
                "equity": equity,
                "lot": lot,
                "open_price": open_price,
                "sl": sl,
                "tp": tp,
                "result": result,
                "note": note,
                "equity_after": equity_after
            }}
        )
        return redirect('/')

    trade = collection.find_one({"_id": ObjectId(id), "username": username})
    trades = list(collection.find({"username": username}).sort("date", -1))
    tp_count = sum(1 for t in trades if t['result'] == 'TP')
    sl_count = sum(1 for t in trades if t['result'] == 'SL')
    total = len(trades)
    start_equity = trades[-1]['equity'] if trades else 0
    end_equity = trades[0]['equity_after'] if trades else 0
    winrate = round((tp_count / total) * 100, 2) if total else 0

    stats = {
        "tp": tp_count,
        "sl": sl_count,
        "total": total,
        "winrate": winrate,
        "growth": end_equity - start_equity
    }

    return render_template_string(HTML_TEMPLATE, trades=trades, stats=stats, edit_data=trade)

@app.route('/delete/<id>')
def delete(id):
    check = protect()
    if check: return check

    username = session["username"]
    collection.delete_one({"_id": ObjectId(id), "username": username})
    return redirect('/')

@app.route('/export')
def export():
    check = protect()
    if check: return check

    username = session["username"]
    trades = list(collection.find({"username": username}).sort("date", -1))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Tanggal', 'Equity', 'Lot', 'Open Price', 'SL', 'TP', 'Hasil', 'Keterangan', 'Equity After'])
    for t in trades:
        writer.writerow([t['date'], t['equity'], t['lot'], t['open_price'], t['sl'], t['tp'], t['result'], t['note'], t['equity_after']])

    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), mimetype='text/csv', as_attachment=True, download_name='jurnal_trading.csv')

if __name__ == '__main__':
   app.run(host='0.0.0.0', port=5000, debug=True)
