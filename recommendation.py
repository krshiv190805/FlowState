import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
import db

def get_profile_features(pref):
    if pref['preferred_study_time'] == 'Morning':
        pst = 8.0
        wake = 6.0
    elif pref['preferred_study_time'] == 'Afternoon':
        pst = 14.0
        wake = 7.5
    else:
        pst = 20.0
        wake = 9.0
    sleep_time = (24.0 - pref['sleep_hours'] + wake) % 24
    return [pst, sleep_time, wake, pref['study_hours_per_day']]

def get_learning_profile(user_id):
    records = db.execute_query("SELECT * FROM preferences")
    if not records or len(records) < 3:
        return "Night Learner"

    df_prefs = pd.DataFrame(records)
    feature_matrix = np.array([get_profile_features(r) for r in records])
    
    cluster_model = KMeans(n_clusters=3, random_state=42, n_init='auto')
    labels = cluster_model.fit_predict(feature_matrix)
    
    centroids_study_start = cluster_model.cluster_centers_[:, 0]
    sorted_clusters = np.argsort(centroids_study_start)
    
    cluster_mapping = {
        sorted_clusters[0]: "Morning Learner",
        sorted_clusters[1]: "Afternoon Learner",
        sorted_clusters[2]: "Night Learner"
    }
    
    matching_idx = df_prefs[df_prefs['user_id'] == user_id].index
    if len(matching_idx) > 0:
        return cluster_mapping[labels[matching_idx[0]]]
    return "Night Learner"

def predict_productivity(sleep, study, gym, assignments, classes, breaks):
    np.random.seed(42)
    sample_size = 200
    
    syn_sleep = np.random.uniform(4.0, 10.0, sample_size)
    syn_study = np.random.uniform(1.0, 8.0, sample_size)
    syn_gym = np.random.uniform(0.0, 3.0, sample_size)
    syn_assign = np.random.randint(0, 8, sample_size)
    syn_class = np.random.randint(0, 15, sample_size)
    syn_breaks = np.random.uniform(0.0, 8.0, sample_size)
    
    base_scores = (
        50.0 
        + np.where(syn_sleep >= 7.0, 15.0, -10.0) 
        + np.where((syn_study >= 3.0) & (syn_study <= 6.0), 15.0, -5.0)
        + np.where(syn_gym >= 0.5, 10.0, -5.0)
        + (syn_breaks * 3.0 - np.where(syn_breaks < 1.5, 10.0, 0.0))
        - (syn_assign * 2.0) - (syn_class * 0.5)
    )
    target_scores = np.clip(base_scores + np.random.normal(0, 3, sample_size), 0, 100)
    
    X_train = np.column_stack([syn_sleep, syn_study, syn_gym, syn_assign, syn_class, syn_breaks])
    regressor = RandomForestRegressor(n_estimators=50, random_state=42)
    regressor.fit(X_train, target_scores)
    
    features_input = np.array([[sleep, study, gym, assignments, classes, breaks]])
    score_pred = regressor.predict(features_input)[0]
    
    suggestions = []
    if sleep < 7.0:
        suggestions.append("Increase sleep by 1 hour.")
    if study > 6.0:
        suggestions.append("Reduce continuous study sessions.")
    if study < 3.0:
        suggestions.append("Allocate more dedicated study slots to stay on track.")
    if gym < 0.8:
        suggestions.append("Schedule short gym blocks to boost energy levels.")
        
    return int(score_pred), suggestions
