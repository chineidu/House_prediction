import numpy as np
import pandas as pd
import re
import os
from typing import List
import pickle
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor

### Helper Functions
def load_data() -> pd.DataFrame:
    """Load data from a directory and covert into a single dataframe.

    Returns:
        pd.DataFrame: A dataframe containing the loaded data.
    """
    # load the csv files in the 'data' directory and save it in a list
    files = [file for file in os.listdir("data/")]
    all_df = pd.DataFrame()  # empty dataframe
    for file in files:
        df = pd.read_csv(f"data/{file}")  # read each file
        all_df = pd.concat([all_df, df], axis="index")  # concatenate each file
    return all_df


def get_address(addr: str) -> str:
    """Clean the text.

    Args:
        text (str): Raw Address.

    Returns:
        str: Cleaned Address.
    """
    result = addr.split(",")[-2:-1]  # select the city
    result = [x.strip() for x in result]  # remove the white spaces
    result = ", ".join(result)  # join on spaces (no longer a list)
    return result


def clean_text(text: str) -> str:
    """Clean the text and extract the numerical details.
    Args:
        text (str): Raw Text.

    Returns:
        str: Cleaned Text.
    """
    pattern = r"\D+"  # non-digits
    result = re.sub(pattern, "", text, flags=re.I)
    return result


def extract_details(text: str) -> str:
    """It extracts the details from the description. It returns a string.

    Args:
        text (str): Raw Text.

    Returns:
        str: Cleaned Text.
    """
    pattern = (
                r"house|terraced|semi-detached|detached|block of flats|duplex|bungalow|mansion"
              )
    result = re.findall(pattern, text, flags=re.I)
    # convert to a string
    result = " ".join(result)
    return result.title()  # title case


def load_estimator() -> "estimator":
    """Load the trained model

    Returns:
        Pickled object: Load a trained model.
    """
    # load the model
    with open("./model/estimator.pkl", "rb") as f:
        loaded_estimators = pickle.load(f)
    return loaded_estimators


###############################################################################################################################################
# main function
def clean_data_n_return_estimator(data: pd.DataFrame) -> "pickle file":
    """
    ====================================================================
    Clean and tranform the features.
    """
    df = data.copy()
    ### drop the missing values
    df = df.dropna()
    # clean the data
    for col in df.columns:
        if col == "address":
            df[col] = df[col].apply(get_address)
        elif col == "title":
            df[col] = df[col].apply(extract_details)
        elif col != "title" or col != "address":
            df[col] = df[col].apply(clean_text)

    # convert to numeric data type
    for col in ["bed", "bath", "toilet", "pkn_space", "price"]:
        df[col] = pd.to_numeric(df[col])

    # select houses with bedrooms between 2 and 7
    df = df.loc[(df["bed"] > 1) & (df["toilet"] < 8)]
    # select houses with bathrooms between 2 and 7
    df = df.loc[(df["bath"] > 1) & (df["bath"] < 8)]
    # select houses with pkn_space between 1 and 10
    df = df.loc[(df["pkn_space"] > 2) & (df["pkn_space"] < 11)]
    #  outliers for price
    cut_off = np.percentile(df["price"], 96)  # remove prices above the 96th percentile
    df = df.loc[df["price"] <= cut_off]
    # fill the missing values in 'pkn_space' with the median value
    median = df["pkn_space"].median()
    df["pkn_space"] = np.where(pd.isna(df["pkn_space"]), median, df["pkn_space"])

    # rename column
    df = df.rename(columns={"title": "type"})
    df = df.rename(columns={"address": "location"})

    # select the locations by creating a pivot table. sort in descending number of count
    addr_count = pd.crosstab(index=df["location"], columns="Count").apply(lambda x: x.sort_values(ascending=False))
    addr_count.columns = ["Count"]  # rename column
    addr_count = addr_count.reset_index()[:15] # reset the index and select the top 15 locations
    locations = [*addr_count["location"].values]  # add the locations and store in a list

    # Filter out locations with fewer counts
    df = df.loc[df["location"].isin(locations)]
    # encode the features
    le_type = LabelEncoder()
    le_location = LabelEncoder()
    df["type"] = le_type.fit_transform(df["type"])
    df["location"] = le_location.fit_transform(df["location"])
    # transform the price
    df["log_price"] = df["price"].apply(lambda price: np.log(price + 1))
    # drop the 'price'
    df = df.drop(columns=["price"])
    X = df.drop(columns=["log_price"])
    y = df["log_price"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=123)
    # train the model with the optimal hyperparameters
    reg = RandomForestRegressor(max_depth=12, n_estimators=90, random_state=123)
    # fit
    reg.fit(X_train, y_train)

    # save the model
    model = {}
    model["reg"] = reg
    model["type"] = le_type
    model["location"] = le_location
    with open("./model/estimator.pkl", "wb") as f:
        pickle.dump(model, f)


if __name__ == "__main__":
    # load the data
    df = load_data()
    # clean the data and return an estimator
    clean_data_n_return_estimator(df)
