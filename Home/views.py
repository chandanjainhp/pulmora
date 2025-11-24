from django.shortcuts import render, redirect
from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import datetime
import io
from xhtml2pdf import pisa
from PyPDF2 import PdfReader, PdfWriter
import base64
# Create your views here.
def home(request):
    return render(request,"home.html")
def signup(request):
    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        username = request.POST['username']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        email = request.POST['email']
        if password1 == password2:
            if User.objects.filter(username=username).exists():
                messages.info(request, 'Username Taken')
                return redirect('signup')
            elif User.objects.filter(email=email).exists():
                messages.info(request, 'Email already exists')
            else:
                user = User.objects.create_user(username=username, password=password1, email=email,first_name=first_name, last_name=last_name)
                user.save();
                print("User Created")
                return redirect('signin')
        else:
            messages.info(request, 'Password not matching..')
            return redirect('signup')
        return redirect('/')
    else:
        return render(request, 'signup.html')
def signin(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)
            return redirect('predict')
        else:
            messages.info(request, 'invalid credentials')
            return redirect('signin')
    else:
        return render(request, 'signin.html')
# Helper function to convert HTML to PDF
def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None

# Helper function to calculate insurance premium
def calculate_premium(age, gender, diagnosis, risk_factors):
    # Base premium amount
    base_premium = 50.0

    # Age factor (higher age = higher premium)
    age_factor = age / 10

    # Gender factor (slightly higher for males based on statistical risk)
    gender_factor = 1.1 if gender == 1 else 1.0

    # Diagnosis factor
    if diagnosis == "Positive":
        diagnosis_factor = 3.0
    elif diagnosis == "Medium":
        diagnosis_factor = 1.5
    else:
        diagnosis_factor = 1.0

    # Risk factors calculation
    risk_premium = 0
    premium_factors = []

    # Calculate premium impact for each risk factor
    for factor in risk_factors:
        if factor['name'] == "Age":
            impact = age_factor * 5
            premium_factors.append({
                'name': 'Age Factor',
                'impact': round(impact, 2)
            })
        elif factor['name'] == "Smoking" and factor['value'] > 4:
            impact = factor['value'] * 3
            premium_factors.append({
                'name': 'Smoking',
                'impact': round(impact, 2)
            })
        elif factor['name'] == "Genetic Risk" and factor['value'] > 4:
            impact = factor['value'] * 2.5
            premium_factors.append({
                'name': 'Genetic Risk',
                'impact': round(impact, 2)
            })
        elif factor['name'] == "chronic Lung Disease" and factor['value'] > 4:
            impact = factor['value'] * 2.8
            premium_factors.append({
                'name': 'Chronic Lung Disease',
                'impact': round(impact, 2)
            })
        elif factor['value'] > 5:
            impact = factor['value'] * 1.2
            premium_factors.append({
                'name': factor['name'],
                'impact': round(impact, 2)
            })

        risk_premium += impact if 'impact' in locals() else 0

    # Base premium factor
    premium_factors.append({
        'name': 'Base Premium',
        'impact': base_premium
    })

    # Diagnosis impact
    diagnosis_impact = base_premium * (diagnosis_factor - 1)
    if diagnosis_impact > 0:
        premium_factors.append({
            'name': 'Diagnosis Risk',
            'impact': round(diagnosis_impact, 2)
        })

    # Calculate total premium (in USD)
    total_premium_usd = (base_premium + risk_premium) * diagnosis_factor * gender_factor

    # Convert to Indian Rupees (1 USD = approximately 75 INR)
    inr_conversion_rate = 75
    total_premium_inr = total_premium_usd * inr_conversion_rate

    # Convert premium factors to INR
    for factor in premium_factors:
        factor['impact'] = round(factor['impact'] * inr_conversion_rate, 2)

    return round(total_premium_inr, 2), premium_factors

# Helper function to get doctor recommendations
def get_doctor_recommendation(diagnosis):
    doctors = [
        {
            'name': 'Dr. Sarah Johnson',
            'specialty': 'Pulmonology',
            'hospital': 'Memorial Cancer Institute',
            'contact': '+1 (555) 123-4567',
            'recommendation': 'Recommended for comprehensive lung evaluation and treatment planning.'
        },
        {
            'name': 'Dr. Michael Chen',
            'specialty': 'Oncology',
            'hospital': 'City Medical Center',
            'contact': '+1 (555) 987-6543',
            'recommendation': 'Specializes in early-stage lung cancer treatment with minimally invasive approaches.'
        },
        {
            'name': 'Dr. Emily Rodriguez',
            'specialty': 'Thoracic Surgery',
            'hospital': 'University Hospital',
            'contact': '+1 (555) 456-7890',
            'recommendation': 'Expert in surgical interventions for lung conditions with advanced robotic techniques.'
        }
    ]

    if diagnosis == "Positive":
        return doctors[1]  # Oncologist for positive diagnosis
    elif diagnosis == "Medium":
        return doctors[0]  # Pulmonologist for medium risk
    else:
        return doctors[2]  # Thoracic surgeon for general cases

def predict(request):
    if (request.method == 'POST'):
        # Check if the request is for generating a PDF
        generate_pdf = 'generate_pdf' in request.POST

        # Get form data
        Age = int(request.POST['Age'])
        Gender = int(request.POST['Gender'])
        Air_Pollution = int(request.POST['Air Pollution'])
        Alcohol_use = int(request.POST['Alcohol use'])
        Dust_Allergy = int(request.POST['Dust Allergy'])
        OccuPational_Hazards = int(request.POST['OccuPational Hazards'])
        Genetic_Risk = int(request.POST['Genetic Risk'])
        chronic_Lung_Disease = int(request.POST['chronic Lung Disease'])
        Balanced_Diet = int(request.POST['Balanced Diet'])
        Obesity = int(request.POST['Obesity'])
        Smoking = int(request.POST['Smoking'])
        Passive_Smoker = int(request.POST['Passive Smoker'])
        Chest_Pain = int(request.POST['Chest Pain'])
        Coughing_of_Blood = int(request.POST['Coughing of Blood'])
        Fatigue = int(request.POST['Fatigue'])
        Weight_Loss = int(request.POST['Weight Loss'])
        Shortness_of_Breath = int(request.POST['Shortness of Breath'])
        Wheezing = int(request.POST['Wheezing'])
        Swallowing_Difficulty = int(request.POST['Swallowing Difficulty'])
        Clubbing_of_Finger_Nails = int(request.POST['Clubbing of Finger Nails'])
        Frequent_Cold = int(request.POST['Frequent Cold'])
        Dry_Cough = int(request.POST['Dry Cough'])
        Snoring = int(request.POST['Snoring'])

        # Run prediction model
        df = pd.read_csv(r"static/dataset/lungcancer.csv")
        labels = df.columns[0:-1]
        X = df[labels]
        X = np.asarray(X, dtype='float64')
        Y = df['Level']
        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.25, random_state=1)
        reg = LogisticRegression()
        reg.fit(X_train, Y_train)
        model = reg
        predic = np.array([[Age,Gender,Air_Pollution,Alcohol_use,Dust_Allergy,OccuPational_Hazards,Genetic_Risk,chronic_Lung_Disease ,Balanced_Diet ,Obesity,Smoking ,Passive_Smoker,Chest_Pain ,Coughing_of_Blood ,Fatigue ,Weight_Loss,Shortness_of_Breath,Wheezing,Swallowing_Difficulty,Clubbing_of_Finger_Nails,Frequent_Cold,Dry_Cough,Snoring]])
        predic.reshape(-1,1)
        pred = model.predict(predic)
        diagnosis_code = pred[0]

        if (diagnosis_code == 1):
            diagnosis = "Positive"
        elif(diagnosis_code == 0):
            diagnosis = "Medium"
        else:
            diagnosis = "Negative"

        # Create risk factors list
        risk_factors = [
            {'name': 'Age', 'value': Age, 'risk_level': 'High' if Age > 60 else 'Medium' if Age > 40 else 'Low'},
            {'name': 'Air Pollution', 'value': Air_Pollution, 'risk_level': 'High' if Air_Pollution > 6 else 'Medium' if Air_Pollution > 3 else 'Low'},
            {'name': 'Alcohol use', 'value': Alcohol_use, 'risk_level': 'High' if Alcohol_use > 6 else 'Medium' if Alcohol_use > 3 else 'Low'},
            {'name': 'Dust Allergy', 'value': Dust_Allergy, 'risk_level': 'High' if Dust_Allergy > 6 else 'Medium' if Dust_Allergy > 3 else 'Low'},
            {'name': 'OccuPational Hazards', 'value': OccuPational_Hazards, 'risk_level': 'High' if OccuPational_Hazards > 6 else 'Medium' if OccuPational_Hazards > 3 else 'Low'},
            {'name': 'Genetic Risk', 'value': Genetic_Risk, 'risk_level': 'High' if Genetic_Risk > 6 else 'Medium' if Genetic_Risk > 3 else 'Low'},
            {'name': 'chronic Lung Disease', 'value': chronic_Lung_Disease, 'risk_level': 'High' if chronic_Lung_Disease > 6 else 'Medium' if chronic_Lung_Disease > 3 else 'Low'},
            {'name': 'Smoking', 'value': Smoking, 'risk_level': 'High' if Smoking > 6 else 'Medium' if Smoking > 3 else 'Low'},
            {'name': 'Passive Smoker', 'value': Passive_Smoker, 'risk_level': 'High' if Passive_Smoker > 6 else 'Medium' if Passive_Smoker > 3 else 'Low'},
            {'name': 'Chest Pain', 'value': Chest_Pain, 'risk_level': 'High' if Chest_Pain > 6 else 'Medium' if Chest_Pain > 3 else 'Low'},
            {'name': 'Coughing of Blood', 'value': Coughing_of_Blood, 'risk_level': 'High' if Coughing_of_Blood > 6 else 'Medium' if Coughing_of_Blood > 3 else 'Low'},
        ]

        # Calculate insurance premium
        premium_amount, premium_factors = calculate_premium(Age, Gender, diagnosis, risk_factors)

        # Get doctor recommendation
        doctor = get_doctor_recommendation(diagnosis)

        # Generate digital signature
        digital_signature = f"Verified by LC Cancer Prediction System on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Store results in session for later use
        request.session['prediction_results'] = {
            'diagnosis': diagnosis,
            'age': Age,
            'gender': Gender,
            'risk_factors': risk_factors,
            'premium_amount': premium_amount,
            'premium_factors': premium_factors,
            'doctor': doctor,
            'digital_signature': digital_signature,
            'report_date': datetime.datetime.now().strftime('%Y-%m-%d')
        }

        # No longer showing diagnosis message at the top
        # messages.info(request, f"Diagnosis: {diagnosis} | Insurance Premium: ₹{premium_amount}/month")

        # If generate_pdf is requested, create and return the PDF
        if generate_pdf:
            # Get user information
            user = request.user

            # Prepare context for PDF template
            context = {
                'user': user,
                'diagnosis': diagnosis,
                'age': Age,
                'gender': Gender,
                'risk_factors': risk_factors,
                'premium_amount': premium_amount,
                'premium_factors': premium_factors,
                'doctor': doctor,
                'digital_signature': digital_signature,
                'report_date': datetime.datetime.now().strftime('%Y-%m-%d')
            }

            # Generate PDF
            pdf = render_to_pdf('insurance_report.html', context)

            if pdf:
                response = HttpResponse(pdf, content_type='application/pdf')
                filename = f"Lung_Cancer_Insurance_Report_{user.username}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
                content = f"inline; filename={filename}"
                response['Content-Disposition'] = content
                return response

            return HttpResponse("Error generating PDF", status=400)

        # Return to prediction page with results
        return render(request, "predict.html", {
            'show_results': True,
            'diagnosis': diagnosis,
            'premium_amount': premium_amount,
            'doctor': doctor,
            'age': Age,
            'gender': Gender,
            'air_pollution': Air_Pollution,
            'alcohol_use': Alcohol_use,
            'dust_allergy': Dust_Allergy,
            'occupational_hazards': OccuPational_Hazards,
            'genetic_risk': Genetic_Risk,
            'chronic_lung_disease': chronic_Lung_Disease,
            'balanced_diet': Balanced_Diet,
            'obesity': Obesity,
            'smoking': Smoking,
            'passive_smoker': Passive_Smoker,
            'chest_pain': Chest_Pain,
            'coughing_of_blood': Coughing_of_Blood,
            'fatigue': Fatigue,
            'weight_loss': Weight_Loss,
            'shortness_of_breath': Shortness_of_Breath,
            'wheezing': Wheezing,
            'swallowing_difficulty': Swallowing_Difficulty,
            'clubbing_of_finger_nails': Clubbing_of_Finger_Nails,
            'frequent_cold': Frequent_Cold,
            'dry_cough': Dry_Cough,
            'snoring': Snoring
        })

    return render(request, "predict.html", {'show_results': False})
def logout(request):
    auth.logout(request)
    return redirect('/')

