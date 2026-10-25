from flask import Flask, render_template_string
import csv
import os

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NAZON Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: monospace; background: #111; color: #eee; padding: 15px; }
        table { border-collapse: collapse; width: 100%; font-size: 12px; }
        th, td { border: 1px solid #333; padding: 6px; text-align: left; }
        th { background: #222; }
        .win { color: #4f4; }
        .loss { color: #f44; }
        .open { color: #ff4; }
        h1 { font-size: 18px; }
        .summary { margin: 10px 0; padding: 10px; background: #222; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>NAZON Forward Log</h1>
    <div class="summary">{{ summary }}</div>
    <table>
        <tr><th>#</th><th>Time</th><th>Symbol</th><th>Dir</th><th>Conf</th><th>Entry</th><th>Outcome</th><th>R</th></tr>
        {% for row in rows %}
        <tr>
            <td>{{ loop.index }}</td>
            <td>{{ row[0][:16] if row[0] else '' }}</td>
            <td>{{ row[1] if row|length > 1 else '' }}</td>
            <td>{{ row[2] if row|length > 2 else '' }}</td>
            <td>{{ row[3] if row|length > 3 else '' }}</td>
            <td>{{ row[4] if row|length > 4 else '' }}</td>
            <td class="{{ 'win' if row|length > 10 and row[10]=='WIN' else 'loss' if row|length > 10 and row[10]=='LOSS' else 'open' }}">
                {{ row[10] if row|length > 10 else 'OPEN' }}
            </td>
            <td>{{ row[12] if row|length > 12 else '' }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

@app.route('/')
def index():
    rows = []
    wins, losses, open_count = 0, 0, 0
    log_file = "nazon_forward_log.csv"
    
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            reader = csv.reader(f)
            data = list(reader)
            if len(data) > 1:
                rows = data[1:]
                for row in rows:
                    if len(row) > 10:
                        if row[10] == "WIN":
                            wins += 1
                        elif row[10] == "LOSS":
                            losses += 1
                        else:
                            open_count += 1
    
    total = wins + losses
    wr = f"{(wins/total*100):.0f}%" if total > 0 else "—"
    summary = f"{open_count} open | {wins} wins | {losses} losses | Win rate: {wr}"
    
    return render_template_string(HTML, rows=rows, summary=summary)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
