import os
import threading
from typing import Any

from fastapi import FastAPI, HTTPException

from classification import load_tfidf_trending_topics
from clustering import load_cluster_insights
from config import load_app_config
from mappers import map_cluster_insights
from spark.listener_runner import listen_and_retrain

app = FastAPI(title="Wikipedia Insights API", version="1.0.0")
_listener_lock = threading.Lock()
_listener_thread: threading.Thread | None = None


def _start_listener_once() -> None:
    global _listener_thread

    with _listener_lock:
        if _listener_thread is not None and _listener_thread.is_alive():
            return

        def run_listener() -> None:
            try:
                listen_and_retrain()
            except Exception as err:
                print(f"[ML] Listener thread stopped with error: {err}")

        _listener_thread = threading.Thread(
            target=run_listener,
            name="ml-listener-retrain",
            daemon=True,
        )
        _listener_thread.start()


@app.on_event("startup")
def startup_listener() -> None:
    # Always run retrain listener with the API process.
    _start_listener_once()


@app.get("/power-editors")
def get_power_editors() -> dict[str, Any]:
    try:
        raw_insights = load_cluster_insights()
        return map_cluster_insights(raw_insights)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to load cluster insights: {err}") from err


@app.get("/power-editors/raw")
def get_power_editors_raw() -> dict[str, Any]:
    try:
        return {"data": load_cluster_insights()}
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to load cluster insights: {err}") from err


@app.get("/trending-topics")
def get_trending_topics() -> dict[str, Any]:
    try:
        app_config = load_app_config()
        return load_tfidf_trending_topics(app_config.model.model_path)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to load trending topics: {err}") from err


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
