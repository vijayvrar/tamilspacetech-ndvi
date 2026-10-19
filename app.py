from datetime import date
import io
import base64
import gc
import matplotlib

# Use non-interactive backend for web servers
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, render_template, request, jsonify
import odc.stac
from odc.stac import load
from pystac_client import Client

app = Flask(__name__)

# Connect to Element 84 Earth Search STAC API
client = Client.open("https://earth-search.aws.element84.com/v1")

# Configure rasterio for anonymous AWS cloud access
odc.stac.configure_rio(cloud_defaults=True, aws={"aws_unsigned": True})


@app.route("/", methods=["GET"])
def index():
    lat = 13.0674
    lon = 80.2376
    return render_template("index.html", lat=lat, lon=lon)


@app.route("/get_ndvi_year", methods=["POST"])
def get_ndvi_year():
    try:
        data = request.get_json()
        lat = float(data["lat"])
        lon = float(data["lon"])
        year = int(data["year"])

        # Small bounding box to keep RAM usage minimal
        delta = 0.02
        bbox = [lon - delta, lat - delta, lon + delta, lat + delta]
        date_range = f"{year}-01-01/{year}-12-31"

        search = client.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=date_range,
            query={"eo:cloud_cover": {"lt": 5}},
            limit=3,
        )
        items = list(search.items())
        if not items:
            return jsonify({"error": f"No cloud-free images found for {year}."})

        item = items[0]
        date_str = item.properties["datetime"][:10]

        # Load bands directly from cloud
        ds = load([item], bands=["red", "nir"], bbox=bbox, resolution=10)
        red = ds["red"].isel(time=0).values.astype(np.float32)
        nir = ds["nir"].isel(time=0).values.astype(np.float32)

        # Calculate NDVI
        np.seterr(divide="ignore", invalid="ignore")
        ndvi = (nir - red) / (nir + red)
        ndvi = np.nan_to_num(ndvi)

        # Generate lightweight plot
        plt.figure(figsize=(5, 5))
        im = plt.imshow(ndvi, cmap="RdYlGn", vmin=-0.2, vmax=1.0)
        plt.colorbar(im, label="NDVI Value", fraction=0.046, pad=0.04)
        plt.title(
            f"NDVI Map ({year})\nCaptured: {date_str}",
            fontsize=10,
            fontweight="bold",
        )
        plt.axis("off")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=100)
        buf.seek(0)
        plt.close("all")

        image_data = base64.b64encode(buf.getvalue()).decode("utf-8")
        
        # Clean up memory explicitly
        del red, nir, ndvi, buf
        gc.collect()

        return jsonify({
            "image": f"data:image/png;base64,{image_data}",
            "date": date_str
        })

    except Exception as e:
        gc.collect()
        return jsonify({"error": f"An error occurred: {str(e)}"})


if __name__ == "__main__":
    app.run(debug=True)
