import pandas as pd
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import io
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

app = FastAPI()

class RouteRequest(BaseModel):
    origem: str
    destino: str

def try_different_encodings(file_content: bytes) -> pd.DataFrame:
    encodings = ['utf-8', 'latin1']
    for encoding in encodings:
        try:
            return pd.read_csv(io.BytesIO(file_content), encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Não foi possível decodificar o arquivo CSV com as codificações tentadas.")

def get_coordinates(address):
    geolocator = Nominatim(user_agent="myGeocoder")
    try:
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
        else:
            return (None, None)
    except GeocoderTimedOut:
        return get_coordinates(address)
    except:
        return (None, None)

def process_routes(routes: List[RouteRequest]):
    m = folium.Map(location=[-23.550520, -46.633308], zoom_start=12)
    
    for route in routes:
        lat_orig, lon_orig = get_coordinates(route['origem'])
        lat_dest, lon_dest = get_coordinates(route['destino'])
        if lat_orig is not None and lon_orig is not None:
            folium.Marker([lat_orig, lon_orig], tooltip=route['origem'], icon=folium.Icon(color='green')).add_to(m)
        if lat_dest is not None and lon_dest is not None:
            folium.Marker([lat_dest, lon_dest], tooltip=route['destino'], icon=folium.Icon(color='red')).add_to(m)
        if lat_orig is not None and lon_orig is not None and lat_dest is not None and lon_dest is not None:
            folium.PolyLine(locations=[(lat_orig, lon_orig), (lat_dest, lon_dest)], color='blue').add_to(m)

    return m._repr_html_()

@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = try_different_encodings(contents)
        if df.empty:
            return {"error": "O arquivo CSV está vazio ou não contém dados estruturados."}
        
        routes = df.to_dict(orient="records")
        map_html = process_routes(routes)
        return HTMLResponse(content=map_html, status_code=200)
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def main():
    content = """
    <html>
        <head>
            <title>Upload de CSV</title>
        </head>
        <body>
            <h1>Upload de CSV</h1>
            <form action="/upload-csv" enctype="multipart/form-data" method="post">
                <input name="file" type="file">
                <button type="submit">Enviar CSV</button>
            </form>
        </body>
    </html>
    """
    return HTMLResponse(content=content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)