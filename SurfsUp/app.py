# Import the dependencies.
import numpy as np
import pandas as pd
import datetime as dt

import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
from sqlalchemy import desc

from flask import Flask, jsonify


#################################################
# Database Setup
#################################################
engine = create_engine("sqlite:///Resources/hawaii.sqlite")

# reflect an existing database into a new model
Base = automap_base()   
# reflect the tables
Base.prepare(autoload_with= engine)

# Save references to each table
Station = Base.classes.station
Measurement = Base.classes.measurement

# Create our session (link) from Python to the DB
    #I opened and closed the sessions at the app.route level instead of here

#################################################
# Flask Setup
#################################################
app = Flask(__name__)

#################################################
# Flask Routes
#################################################
@app.route("/")
def home():
    """List all available api routes."""
    return (
        f"Available Routes:<br/>"
        f"Last 12 months of precipitation data (2016-08-23 to 2017-08-23): /api/v1.0/precipitation<br/>"
        f"List of all stations: /api/v1.0/stations<br/>"
        f"Temperatures for most active station (USC00519281) over the last year: /api/v1.0/tobs<br/>"
        f"Get a list of the minimum, average, and maximum temperature for a specified start or start-end range:<br/>"
            f"  Example of start range: /api/v1.0/2017-08-10<br/>"
            f"  Example of start-end range: /api/v1.0/2017-08-10/2017-08-15<br/>"
    )

@app.route("/api/v1.0/precipitation")
def precipitation():
    # Create our session (link) from Python to the DB
    session = Session(engine)

    #Query results from precipitation analysis for last 12 months of data
    most_recent_measurement = session.query(Measurement).order_by(desc(Measurement.date)).first().date
    most_recent_date = dt.datetime.strptime(most_recent_measurement, '%Y-%m-%d').date()
    last_12_months_date = most_recent_date - dt.timedelta(days=365)
    last_12_months_precipitation = session.query(Measurement.date, Measurement.prcp).filter(Measurement.date >= last_12_months_date).all()

    #Close the session
    session.close()

    # Convert the query results to a dictionary (date: precipitation)
    precipitation_dict = {date: prcp for date, prcp in last_12_months_precipitation}

    # Return the JSON representation of the dictionary
    return jsonify(precipitation_dict)

@app.route("/api/v1.0/stations")
def stations():
    # Create our session (link) from Python to the DB
    session = Session(engine)

    #Find station names
    stations = session.query(Station.station).distinct().all()
  
    #Close the session
    session.close()

    # Convert list of tuples into normal list
    stations_list = list(np.ravel(stations))

    return jsonify(stations_list)

@app.route("/api/v1.0/tobs")
def tobs():
    # Create our session (link) from Python to the DB
    session = Session(engine)

    #Find the last 12 months of data from most active station
    most_recent_station_date = session.query(Measurement).filter(Measurement.station == 'USC00519281')\
    .order_by(desc(Measurement.date)).first().date
    recent_station_date = dt.datetime.strptime(most_recent_station_date, '%Y-%m-%d').date()
    one_year_ago_station_date = recent_station_date - dt.timedelta(days=365)

    active_station_data = session.query(Measurement).filter(
    Measurement.station == 'USC00519281',
    Measurement.date >= one_year_ago_station_date).all()

    #Close the session
    session.close()

    # Convert data into a list of dictionaries with date and temperature observation
    temperature_data = [{'date': record.date, 'tobs': record.tobs} for record in active_station_data]

    # Return the JSON representation of the temperature data
    return jsonify(temperature_data)

@app.route("/api/v1.0/<start>", defaults={'end': None})
@app.route("/api/v1.0/<start>/<end>")
def temp_stats(start, end):
    # Create session (link) from Python to the DB
    session = Session(engine)

    #Convert date from string to date object
    try:
        start_date = dt.datetime.strptime(start, '%Y-%m-%d').date()
    except ValueError:
        return abort(400, description="Invalid start date format. Use YYYY-MM-DD.")

    # If no end date is provided, retrieve the last date in the database
    if end is None:
        last_date = session.query(func.max(Measurement.date)).scalar()
        if last_date is None:
            return abort(404, description="No data available.")
        end_date = dt.datetime.strptime(last_date, '%Y-%m-%d').date()
    else:
        try:
            end_date = dt.datetime.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            return abort(400, description="Invalid end date format. Use YYYY-MM-DD.")
   
    # Query for temperature statistics based on provided dates
    results = session.query(
        func.min(Measurement.tobs), 
        func.avg(Measurement.tobs), 
        func.max(Measurement.tobs)
    ).filter(Measurement.date >= start_date).filter(Measurement.date <= end_date).all()

    session.close()

    # Check if results are empty
    if not results:
        return jsonify({"error": "No data found for the given date range."}), 404

    # Convert results to a dictionary
    temp_stats = {
        "TMIN": results[0][0],
        "TAVG": results[0][1],
        "TMAX": results[0][2]
    }

    return jsonify(temp_stats)


if __name__ == '__main__':
    app.run(debug=True)