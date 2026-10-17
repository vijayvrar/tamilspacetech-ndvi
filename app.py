from datetime import date
import io
import base64
import matplotlib

# Use non-interactive backend for web servers
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, render_template, request
import odc.stac
from odc.stac import load
from pystac_client import Client

app = Flask(__name__)

# Connect to Element 84 Earth Search STAC API
client = Client.open("https://earth-search.aws.element84.com/v1")

# Configure rasterio for anonymous AWS cloud access
odc.stac.configure_rio(cloud_defaults=True, aws={"aws_unsigned": True})


@app.route("/", methods=["GET", "POST"])
def index():
  image_data = None
  error_msg = None
  captured = None

  # Default values (Chennai Central coordinates)
  lat = 13.0674
  lon = 80.2376
  year = 2025

  if request.method == "POST":
    try:
      lat = float(request.form["lat"])
      lon = float(request.form["lon"])
      year = int(request.form["year"])

      # Create a ~10km bounding box around the lat/long point
      delta = 0.05
      bbox = [lon - delta, lat - delta, lon + delta, lat + delta]

      # Handle date range safely
      current_year = date.today().year
      if year > current_year:
        year = current_year

      date_range = f"{year}-01-01/{year}-12-31"

      # Search for Sentinel-2 L2A items
      search = client.search(
          collections=["sentinel-2-l2a"],
          bbox=bbox,
          datetime=date_range,
          query={"eo:cloud_cover": {"lt": 25}},
          limit=10,
      )
      items = list(search.items())

      if not items:
        error_msg = (
            f"No cloud-free Sentinel-2 images found for {year} in this region."
            " Try an earlier year like 2024 or 2025."
        )
      else:
        item = items[0]
        date_str = item.properties["datetime"][:10]
        captured = date_str

        # Load bands directly from cloud
        ds = load([item], bands=["red", "nir"], bbox=bbox, resolution=10)
        red = ds["red"].isel(time=0).values.astype(np.float32)
        nir = ds["nir"].isel(time=0).values.astype(np.float32)

        # Calculate NDVI
        np.seterr(divide="ignore", invalid="ignore")
        ndvi = (nir - red) / (nir + red)
        ndvi = np.nan_to_num(ndvi)

        # Generate plot and save to memory buffer instead of hard drive
        plt.figure(figsize=(6, 6))
        im = plt.imshow(ndvi, cmap="RdYlGn", vmin=-0.2, vmax=1.0)
        plt.colorbar(im, label="NDVI Value", fraction=0.046, pad=0.04)
        plt.title(
            f"NDVI Map ({year})\nCaptured: {date_str}",
            fontsize=11,
            fontweight="bold",
        )
        plt.axis("off")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        buf.seek(0)
        plt.close()

        # Encode image to Base64 string for direct HTML embedding
        image_data = base64.b64encode(buf.getvalue()).decode("utf-8")

    except Exception as e:
      error_msg = f"An error occurred: {str(e)}"

  return render_template(
      "index.html",
      image_data=image_data,
      error_msg=error_msg,
      captured=captured,
      lat=lat,
      lon=lon,
      year=year,
  )


if __name__ == "__main__":
  app.run(debug=True)