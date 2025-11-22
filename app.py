from flask import Flask,render_template,request,session
from condition import clouds,mist_conditions,drizzle,rain,thunderstorm,snow,icon_map
from flask_limiter import Limiter
from flask_caching import Cache
from flask_limiter.util import get_remote_address 
from collections import defaultdict,Counter
from datetime import datetime,timedelta
from dotenv import load_dotenv
import requests
import os
import re

app = Flask(__name__)
load_dotenv()
API_KEY = os.getenv('API_KEY')
app.secret_key = os.getenv('SECRET_KEY')

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

limiter = Limiter(get_remote_address,app=app,default_limits=["30 per minute"])
cache = Cache(app, config={
    "CACHE_TYPE": "simple",
    "CACHE_DEFAULT_TIMEOUT": 600
})



DEFAULT_ICON = "default.svg"  # Default fallback icon for unknown weather

def get_cloud_icon(cloud_percentage):
    if cloud_percentage <= 10:
        return "clear_sky.svg"
    elif cloud_percentage <= 25:
        return "few_clouds.svg"
    elif cloud_percentage <= 50:
        return "scattered_clouds.svg"
    elif cloud_percentage <= 75:
        return "broken_clouds.svg"
    else:
        return "overcast_clouds.svg"

def clean_city(city):
    return re.sub(r"[^a-zA-Z\s]", "", city).strip()
    
@app.route("/")
def home_page(city=""):
    selected_unit = session.get("unit","metric")
    
    # Determine actual city name first
    if city == "":
        try:
            LOC_DATA = requests.get("http://ip-api.com/json/", timeout=3).json()
            CITY = LOC_DATA['city']
        except Exception as e:
            CITY = "London"
    else:
        CITY = city
    
    # Create cache key with actual city name
    cache_key = f"{CITY.lower()}_{selected_unit}"
    cached_data = cache.get(cache_key)

    if cached_data:
        return render_template(
            "index.html",
            current_weather=cached_data["current_weather"],
            forecast_weather=cached_data["forecast_weather"],
            hours_weather=cached_data["hours_weather"],
            selected_unit=selected_unit
        )

    # Fetch fresh data
    current_url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units={selected_unit}"
    forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={CITY}&appid={API_KEY}&units={selected_unit}"

    try:
        current_data = requests.get(current_url, timeout=5).json()
    except Exception as e:
        return render_template('index.html',error="Weather service not responding",
                               current_weather = session.get('last_current_weather'),
                               forecast_weather = session.get('last_forecast_weather'), 
                               hours_weather = session.get('last_hours_weather'), 
                               selected_unit = selected_unit) 
    
    try:
        forecast_data = requests.get(forecast_url, timeout=5).json()
    except Exception as e:
        return render_template("index.html", error = "Weather service not responding",
                           current_weather = session.get('last_current_weather'),
                           forecast_weather = session.get('last_forecast_weather'), 
                            hours_weather = session.get('last_hours_weather'), 
                            selected_unit = selected_unit)
        
    if current_data.get("cod") != 200:
        return render_template("index.html", error = "City not found",
                               current_weather = session.get('last_current_weather'),
                               forecast_weather = session.get('last_forecast_weather'), 
                                hours_weather = session.get('last_hours_weather'), 
                                selected_unit = selected_unit)

    if selected_unit == "metric":
        u = "°C" 
        wind_u = "m/s"
    elif selected_unit == "imperial":
        u = "°F"
        wind_u = "mph"   
    elif selected_unit == "standard":
        u = "K"
        wind_u = "m/s" 

    location = f"{current_data['sys']['country']},{current_data['name']}"
    zone = current_data['timezone'] / 3600
    if zone >= 0:
        timezone = f"UTC+{zone:.0f}"
    else:
        timezone = f"UTC{zone:.0f}"

    local_time = datetime.utcfromtimestamp(current_data['dt'] + current_data['timezone']).strftime('%I:%M %p')
    sunrise = datetime.fromtimestamp(current_data['sys']['sunrise']).strftime("%I:%M %p")
    sunset = datetime.fromtimestamp(current_data['sys']['sunset']).strftime("%I:%M %p")
    temp = f"{round(current_data['main']['temp'])}{u}"
    feels = f"{round(current_data['main']['feels_like'])}{u}"
    weather_des = current_data['weather'][0]['description']
    humidity = f"{current_data['main']['humidity']}%"
    pressure = f"{current_data['main']['pressure']}hPa"
    wind_speed = f"{current_data['wind']['speed']}{wind_u}"
    visibility = f"{round(current_data['visibility'] / 1000)}km"
    cloud_perc_value = current_data['clouds']['all']
    cloud_perc= f"{current_data['clouds']['all']}%"
    curr_icon = "" 

    if weather_des in clouds:
        curr_icon += get_cloud_icon(cloud_perc_value)
    elif weather_des in drizzle:
        curr_icon += icon_map.get(weather_des, DEFAULT_ICON)
    elif weather_des in rain:
        curr_icon += icon_map.get(weather_des, DEFAULT_ICON)
    elif weather_des in thunderstorm:
        curr_icon += icon_map.get(weather_des, DEFAULT_ICON)
    elif weather_des in snow:
        curr_icon += icon_map.get(weather_des, DEFAULT_ICON)
    elif weather_des in mist_conditions:
        curr_icon += icon_map.get(weather_des, DEFAULT_ICON)
    elif weather_des == "clear sky":
        curr_icon += icon_map.get(weather_des, DEFAULT_ICON)
        weather_des = "Sunny"
    else:
        curr_icon += DEFAULT_ICON  # Fallback for unknown weather

    current_weather = [{
        'location': location,
        'timezone': timezone,
        'time': local_time,
        'sunrise': sunrise,
        'sunset': sunset,
        'temp': temp,
        'feels': feels,
        'weather_des': weather_des,
        'icon' : curr_icon,
        'humidity':humidity,
        'pressure': pressure,
        'wind_speed': wind_speed,
        'visibility': visibility,
        'cloud' : cloud_perc
    }]

    hourly_data = forecast_data['list'][:8]
    hours_weather = []
    for hour in hourly_data:
        time = datetime.strptime(hour['dt_txt'],"%Y-%m-%d %H:%M:%S").strftime("%I %p")
        tem = f"{round(hour['main']['temp'])}{u}"
        temp_likes = f"{round(hour['main']['feels_like'])}{u}"
        desc = hour['weather'][0]['description']
        icon = ""
        hour_cloud = hour['clouds']['all']

        if desc in clouds:
            icon += get_cloud_icon(hour_cloud)
        elif desc in drizzle:
            icon += icon_map.get(desc, DEFAULT_ICON)
        elif desc in rain:
            icon += icon_map.get(desc, DEFAULT_ICON)
        elif desc in thunderstorm:
            icon += icon_map.get(desc, DEFAULT_ICON)
        elif desc in snow:
            icon += icon_map.get(desc, DEFAULT_ICON)
        elif desc in mist_conditions:
            icon += icon_map.get(desc, DEFAULT_ICON)
        elif desc == "clear sky":
            icon += icon_map.get(desc, DEFAULT_ICON)
            desc = 'Sunny'
        else:
            icon += DEFAULT_ICON  # Fallback for unknown weather

        hours_weather.append({
            'time': time,
            'temp': tem,
            'feels':temp_likes,
            'desc': desc,
            'icon': icon
        })

    daily_data = defaultdict(list)
    for item in forecast_data['list']:
        date = item['dt_txt'].split(" ")[0]
        daily_data[date].append(item)

    forecast_weather = []
    for date,entries in daily_data.items():
        temp = [e['main']['temp'] for e in entries]
        humidities = [e['main']['humidity'] for e in entries]
        pressures = [e['main']['pressure'] for e in entries]
        wind_speeds = [e['wind']['speed'] for e in entries]

        descriptions = [e['weather'][0]['description'] for e in entries]
        common_descrip = Counter(descriptions).most_common(1)[0][0]
        fore_icon = ""
        cloud = [e['clouds']['all'] for e in entries]
        fore_cloud = sum(cloud) / len(cloud)

        date_obj = datetime.strptime(date, "%Y-%m-%d")
        link_date = date_obj.strftime("%Y-%m-%d")
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        if date_obj.date() == today:
            formatted_date = "Today"
        elif date_obj.date() == tomorrow:
            formatted_date = "Tomorrow"
        else:
            try:
                formatted_date = date_obj.strftime("%-d %A")
            except:
                formatted_date = date_obj.strftime("%#d %A")

        if common_descrip in clouds:
            fore_icon += get_cloud_icon(fore_cloud)
        elif common_descrip in drizzle:
            fore_icon += icon_map.get(common_descrip, DEFAULT_ICON)
        elif common_descrip in rain:
            fore_icon += icon_map.get(common_descrip, DEFAULT_ICON)
        elif common_descrip in thunderstorm:
            fore_icon += icon_map.get(common_descrip, DEFAULT_ICON)
        elif common_descrip in snow:
            fore_icon += icon_map.get(common_descrip, DEFAULT_ICON)
        elif common_descrip in mist_conditions:
            fore_icon += icon_map.get(common_descrip, DEFAULT_ICON)
        elif common_descrip == "clear sky":
            fore_icon += icon_map.get(common_descrip, DEFAULT_ICON)
            common_descrip = "Sunny"
        else:
            fore_icon += DEFAULT_ICON  # Fallback for unknown weather
            
        city_for_details = current_data['name'] 
        forecast_weather.append({
            'city' :  city_for_details,
            'date': formatted_date,
            'link_date': link_date,
            'avg_temp': f"{round(sum(temp) / len(temp))}{u}",
            'avg_max': f"{round(max(temp))}{u}",
            'avg_min': f"{round(min(temp))}{u}",
            'humidity': round(sum(humidities) / len(humidities)),
            'pressure': round(sum(pressures) / len(pressures)),
            'wind_speed': f"{round(sum(wind_speeds) / len(wind_speeds),1)}{wind_u}",
            'desc': common_descrip,
            'icon': fore_icon
        })

    # Store in session for fallback
    session["last_current_weather"]  = current_weather
    session["last_forecast_weather"] = forecast_weather
    session["last_hours_weather"] = hours_weather

    # Cache the processed data
    cache.set(cache_key, {
        "current_weather": current_weather,
        "forecast_weather": forecast_weather,
        "hours_weather": hours_weather
    })

    return render_template("index.html", 
                           current_weather = current_weather,
                           forecast_weather = forecast_weather, 
                           hours_weather = hours_weather, 
                           selected_unit = selected_unit)

@app.route("/get_unit",methods = ['POST'])
def get_unit():
    data = request.get_json()
    session['unit'] = data.get('unit','metric')
    return {"message": "Unit updated successfully"}

@app.route("/searchCity",methods = ['POST'])
def search_city():
    CITY = clean_city(request.form.get("city_name",""))
    return home_page(CITY)

@app.route("/details/<city>/<date>",methods = ['POST','GET'])
def details_of_day(city,date):
    selected_unit = session.get('unit','metric')
    
    # Cache key for details page
    cache_key = f"details_{city.lower()}_{selected_unit}"
    cached_forecast = cache.get(cache_key)
    
    if cached_forecast:
        forecast_data = cached_forecast
    else:
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units={selected_unit}"
        try:
            forecast_data = requests.get(forecast_url, timeout=5).json()
            # Cache the forecast data
            cache.set(cache_key, forecast_data)
        except Exception as e:
            return render_template("details_date.html", error = "Weather service not responding",
                                    date = date , city = city , weather_list = session.get("last_weather_list"))

    if selected_unit == "metric":
        u = "°C" 
        wind_u = "m/s"
    elif selected_unit == "imperial":
        u = "°F"
        wind_u = "mph"   
    elif selected_unit == "standard":
        u = "K"
        wind_u = "m/s" 

    weather_list = []
    day = None
    for item in forecast_data['list']:
        date_obj = datetime.strptime(item['dt_txt'], "%Y-%m-%d %H:%M:%S").date()
        if str(date_obj) == date:
            day_obj = datetime.strptime(item['dt_txt'],"%Y-%m-%d %H:%M:%S")
            day = day_obj.strftime("%A")
            hour = day_obj.strftime("%I %p")
            temp = item['main']['temp']
            feels = item['main']['feels_like']
            humidity = item['main']['humidity']
            pressure = item['main']['pressure']
            wind_speed = item['wind']['speed']
            desc = item['weather'][0]['description']
            cloud_percent = int(item['clouds']['all'])
            icon = ""    
            if desc in clouds:
                icon += get_cloud_icon(cloud_percent)
            elif desc in drizzle:
                icon += icon_map.get(desc, DEFAULT_ICON)
            elif desc in rain:
                icon += icon_map.get(desc, DEFAULT_ICON)
            elif desc in thunderstorm:
                icon += icon_map.get(desc, DEFAULT_ICON)
            elif desc in snow:
                icon += icon_map.get(desc, DEFAULT_ICON)
            elif desc in mist_conditions:
                icon += icon_map.get(desc, DEFAULT_ICON)
            elif desc == "clear sky":
                icon += icon_map.get(desc, DEFAULT_ICON)
                desc = 'Sunny'
            else:
                icon += DEFAULT_ICON  # Fallback for unknown weather

            weather_list.append({
                'hour': hour,
                'day': day,
                'temp': f"{round(temp)}{u}",
                'feels': f"{round(feels)}{u}",
                'desc': desc,
                'icon': icon,
                'humidity': humidity,
                'pressure': pressure,
                'speed': f"{wind_speed}{wind_u}",
            })

    if not weather_list:
        return render_template("details_date.html", error ="No data found for this date.",
                               date = date, city = city, weather_list = session.get("last_weather_list"))
    
    session["last_weather_list"] = weather_list

    return render_template('details_date.html', date = date, city = city, day = day ,weather_list = weather_list)  

if __name__ == '__main__':
    app.run(debug=True)