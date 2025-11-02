import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import make_pipeline

# 1. Create a Sample Dataset
# In a real-world scenario, you would load your data from a CSV/database.


df = pd.read_excel('./training_data.xlsx')

# Separate features (X) and target (y)
X = df['text']
y = df['category']

# 2. Split the Data
# Split data into training and testing sets (80% train, 20% test)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

# 3. Build a Machine Learning Pipeline
# A pipeline sequentially applies a list of transformers and a final estimator.
# Step 1: TfidfVectorizer (Feature Engineering)
# Step 2: MultinomialNB (Classifier/Model)
model = make_pipeline(
    # Converts text to TF-IDF features, removing common English words
    TfidfVectorizer(stop_words='english'),
    MultinomialNB()                         # Trains the Naive Bayes Classifier
)

# 4. Train the Model
# The .fit() method handles both feature extraction (vectorization) and model training.
print("--- Training Model ---")
model.fit(X_train, y_train)
print("Training Complete.\n")

# 5. Make Predictions
y_pred = model.predict(X_test)

# 6. Evaluate the Model
print("--- Model Evaluation ---")
print(f"Accuracy: {accuracy_score(y_test, y_pred):.2f}\n")
print("Classification Report:")
print(classification_report(y_test, y_pred))

# 7. Test on New Unseen Text
print("--- Testing on New Text ---")
new_texts = [
    " send me a screenshot.",
    "send me photo",
    "A simple update on the situation."
    'start video streaming',
    'initiate remote desktop connection',
    'begin key logging',
    'start screen sharing'

]

predictions = model.predict_proba(new_texts)
print(model.classes_.tolist())  # model.get_feature_names_out()
print(predictions.tolist())

for text, prediction in zip(new_texts, predictions):
    print(
        f"Text: '{text}' -> Predicted Label: {prediction.argmax()}, Probabilities: {prediction.tolist()}")

# Save the trained model for future use
joblib.dump(model, 'text_classifier.joblib')
