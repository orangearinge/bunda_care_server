from typing import List, Dict
import os
import tempfile

# Simple stub for AI food recognition. Replace with real service integration.
_model = None
_model_err = None

def _model_path():
    return os.path.join(os.path.dirname(__file__), "best.pt")

def _load_model():
    global _model, _model_err
    if _model is not None or _model_err is not None:
        return _model
    try:
        from ultralytics import YOLO
        path = _model_path()
        if os.path.exists(path):
            _model = YOLO(path)
            return _model
        else:
            _model_err = FileNotFoundError(path)
            return None
    except Exception as e:
        _model_err = e
        return None

# Simple stub for AI food recognition. Replace with real service integration.
def recognize(image_file) -> List[Dict]:
    filename = getattr(image_file, "filename", "") or ""
    basename = os.path.basename(filename).lower()

    def _map_label(txt: str) -> str:
        t = (txt or "").strip().lower()
        t = t.replace("-", " ")
        t = " ".join(t.split())
        return t

    model = _load_model()
    if model is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(basename or "img")[1] or ".jpg")
        try:
            image_file.stream.seek(0)
            tmp.write(image_file.stream.read())
            tmp.flush()
            tmp.close()

            results = model(tmp.name)
            labels: List[Dict] = []
            try:
                r = results[0]
                names = r.names if hasattr(r, "names") else getattr(model, "names", {})

                # 1) Classification output (YOLO-cls): use probs.top5 and probs.top5conf
                probs = getattr(r, "probs", None)
                if probs is not None:
                    top_idx = getattr(probs, "top5", None)
                    top_conf = getattr(probs, "top5conf", None)
                    try:
                        idx_list = [int(i) for i in (top_idx.tolist() if hasattr(top_idx, "tolist") else (list(top_idx) if top_idx is not None else []))]
                        conf_list = [float(c) for c in (top_conf.tolist() if hasattr(top_conf, "tolist") else (list(top_conf) if top_conf is not None else []))]
                        for i, c in zip(idx_list, conf_list):
                            label = names.get(i, str(i)) if isinstance(names, dict) else str(i)
                            labels.append({"label": str(label), "confidence": c})
                    except Exception:
                        pass

                # 2) Detection output (YOLO-det): use boxes.cls and boxes.conf
                boxes = getattr(r, "boxes", None)
                if boxes is not None:
                    try:
                        cls_tensor = getattr(boxes, "cls", None)
                        conf_tensor = getattr(boxes, "conf", None)
                        if cls_tensor is not None and conf_tensor is not None:
                            cls_list = cls_tensor.tolist() if hasattr(cls_tensor, "tolist") else list(cls_tensor)
                            conf_list = conf_tensor.tolist() if hasattr(conf_tensor, "tolist") else list(conf_tensor)
                            for ci, cf in zip(cls_list, conf_list):
                                i = int(ci)
                                c = float(cf)
                                label = names.get(i, str(i)) if isinstance(names, dict) else str(i)
                                labels.append({"label": str(label), "confidence": c})
                    except Exception:
                        pass

            except Exception:
                pass

            if labels:
                try:
                    labels = [it for it in labels if float(it.get("confidence") or 0) >= 0.15]
                except Exception:
                    pass
                if len(labels) > 20:
                    labels = labels[:20]

                # Deduplicate by label keeping max confidence
                best = {}
                for it in labels:
                    lab = _map_label(it.get("label"))
                    conf = float(it.get("confidence") or 0)
                    if lab and (lab not in best or conf > best[lab]["confidence"]):
                        best[lab] = {"label": lab, "confidence": conf}
                out = list(best.values())
                out.sort(key=lambda x: x.get("confidence", 0), reverse=True)
                return out[:5]
        except Exception:
            pass
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

    vocab = [
        ("ayam", 0.86),
        ("telur", 0.78),
        ("nasi", 0.80),
        ("tempe", 0.74),
        ("tahu", 0.72),
        ("ikan", 0.77),
        ("sayur", 0.70),
        ("brokoli", 0.65),
        ("wortel", 0.66),
        ("kentang", 0.69),
        ("bayam", 0.64),
        ("sapi", 0.73),
        ("udang", 0.71),
    ]
    hits: List[Dict] = []
    for label, conf in vocab:
        if label in basename:
            hits.append({"label": label, "confidence": conf})
    if not hits:
        hits = [
            {"label": "ayam", "confidence": 0.82},
            {"label": "kentang", "confidence": 0.61},
        ]
    return hits[:5]
