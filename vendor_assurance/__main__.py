import argparse
import html
import json
from pathlib import Path
from .core import review, decide


def main():
    parser = argparse.ArgumentParser(description='Offline vendor evidence and renewal review')
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--tenant', required=True)
    parser.add_argument('--as-of', required=True, help='Explicit ISO evaluation date; use current date for actual reviews')
    parser.add_argument('--output', type=Path, required=True, help='New output directory; existing paths are rejected')
    parser.add_argument('--decision', type=Path, help='Local human decision JSON; no authentication implied')
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text())
    report = review(bundle, args.tenant, args.as_of)
    decision = None
    if args.decision:
        fields = json.loads(args.decision.read_text())
        decision = decide(bundle, report, args.tenant, today=args.as_of, **fields)
    args.output.mkdir(parents=True, exist_ok=False)
    package = dict(bundle=bundle, report=report, decision=decision)
    (args.output / 'review.json').write_text(json.dumps(package, indent=2) + '\n')
    esc = html.escape
    cards = ''.join(f'<article><h2>{esc(f["kind"])} · {esc(f["key"])}</h2><p>{esc(f["detail"])}</p>' + ''.join(f'<blockquote>{esc(c["quote"])}<footer>{esc(c["document"])} v{c["version"]} · characters {c["start"]}–{c["end"]}</footer></blockquote>' for c in f['citations']) + '</article>' for f in report['findings'])
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>A2Z Vendor Assurance</title><style>body{font:18px system-ui;background:#101b2a;color:#edf3fc;max-width:1000px;margin:50px auto;padding:24px}article{background:#1d3047;padding:22px;margin:20px 0;border-radius:12px}h1{font-size:42px}footer{font-size:14px;color:#b5c9df}a{color:#85caff}blockquote{border-left:3px solid #85caff;padding-left:20px}</style>'
    page += f'<h1>A2Z Vendor Assurance</h1><p>{esc(report["vendor"])} / {esc(report["service"])} · {esc(args.as_of)}</p><p>{len(report["findings"])} findings · {report["days_to_renewal"]} days to renewal · Human review required</p><p>Offline reference. Operator-supplied claims; no compliance certification or external actions.</p>' + cards
    page += '<p>Decision: ' + esc(decision['outcome'] if decision else 'Pending human review') + '</p><p><a href="https://a2zsoc.com">A2Z SOC</a></p></html>'
    (args.output / 'review.html').write_text(page)
    print(json.dumps(dict(findings=len(report['findings']), decision=decision['outcome'] if decision else None, output=str(args.output))))


if __name__ == '__main__':
    main()
