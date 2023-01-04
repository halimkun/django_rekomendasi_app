import pandas as pd
import numpy as np
import os
import json

from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse

from .forms import UploadFileForm, handle_uploaded_file

from sklearn import tree, preprocessing
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report, precision_score


# constructor for nav menu
def nav_menu(request):
    context = {
        'menu': [
            {'url': '/', 'title': 'Home'},
            {'url': '/rekomendasi/', 'title': 'Rekomendasi'},
            {'url': '/bantuan/', 'title': 'Bantuan'},
            {'url': '/about/', 'title': 'About'},
        ]
    }

    return context


def index(request):
    context = {
        'title': 'RECAPP | Home',
        'nav': nav_menu(request),
        'request': request,
    }

    return render(request, 'index.html', context)


def rekomendasi(request):
    context = {
        'title': 'RECAPP | Rekomendasi',
        'nav': nav_menu(request),
        'request': request,
        'dataset': False,
    }

    if len(os.listdir('media/')) == 0:
        context = context
    else:
        df = pd.read_csv('media/' + os.listdir('media/')[-1])

        last_col = df.iloc[:, -1].value_counts().to_dict()
        last_col = list(last_col.items())

        # drop first and second column
        nilai_df = df.drop(df.columns[[0, 1]], axis=1)
        nilai_df = nilai_df.drop(nilai_df.columns[-1], axis=1)

        col_name = []
        for i in range(len(nilai_df.columns)):
            col_name.append({'key': nilai_df.columns[i].replace(" ", "_").lower() , 'value': nilai_df.columns[i]})
        
        context['dataset'] = True
        context['filename'] = os.listdir('media/')[-1]
        context['input_label'] = col_name
        context['data'] = df
        
    return render(request, 'rekomendasi.html', context)


def bantuan(request):
    context = {
        'title': 'RECAPP | Bantuan',
        'nav': nav_menu(request),
        'request': request,
    }

    return render(request, 'bantuan.html', context)


def about(request):
    context = {
        'title': 'RECAPP | About',
        'nav': nav_menu(request),
        'request': request,
    }

    return render(request, 'about.html', context)


# ==================== REKOMENDASI ==================== #

def print_rekomendasi(request):
    if request.method != 'POST':
        return redirect('/rekomendasi/')
    else:
        # data is key and value from post request
        key = request.POST.dict()
        key.pop('csrfmiddlewaretoken')
        key.pop('prediction')

        # get data from post request
        data = []
        for i in key:
            data.append((key[i].lower()))

        # return JsonResponse(data, safe=False)
        
        return render(request, 'print.html', {
            "key" : key,
            "data" : data,
        })

# ==================== DATASET ==================== #

def get_rekomendasi(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    else:
        if len(os.listdir('media/')) == 0:
            return JsonResponse({'status': 'error', 'message': 'Dataset not found'}, status=404)
        else:
            df = pd.read_csv('media/' + os.listdir('media/')[-1])     # load dataset
            
            # lowercase column name
            df.columns = df.columns.str.lower()
            
            # get numeric column
            df = df.dropna()
            
            # remove outlier
            Q1 = df.quantile(0.25)
            Q3 = df.quantile(0.75)
            IQR = Q3 - Q1
            df = df[~((df < (Q1 - 1.5 * IQR)) | (df > (Q3 + 1.5 * IQR))).any(axis=1)]

            # select numeric column
            numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']
            numdf = df.select_dtypes(include=numerics)     
            numdf = numdf.drop(columns=['no'])     # drop No column cause it's not important but it's numeric

            # get label column
            label = df.iloc[:, -1]

            # initialize min max scaler
            scaler = preprocessing.MinMaxScaler()
            nilai_df = scaler.fit_transform(numdf)

            # split dataset
            x_train, x_test, y_train, y_test = train_test_split(nilai_df, label, test_size=0.3, random_state=42)
            
            # model initialization
            clf = tree.DecisionTreeClassifier(
                max_depth=3,
                splitter='best',
                min_samples_leaf=5,
                criterion='entropy',
            )

            # train model
            clf.fit(nilai_df, label)

            # get accuracy
            y_pred = clf.predict(x_test)
            accuracy = accuracy_score(y_test, y_pred)
    
            # get prediction
            input_data = []
            # get nilai from post request
            for i in range(len(numdf.columns)):
                input_data.append(
                    request.POST.get(numdf.columns[i].replace(" ", "_").lower())
                )


            # convert to numpy array
            input_data = np.array(input_data).reshape(1, -1)

            # scale input data
            input_data = scaler.transform(input_data)

            # get prediction
            prediction = clf.predict(input_data)
            
            # get classificaton report
            report = classification_report(y_test, y_pred)
            # report = pd.DataFrame(report).transpose().to_html()
            # report = report.replace('border="1" class="dataframe"', 'class="table table-bordered table-striped"')
            
            return JsonResponse({
                'status': True,
                'message': 'Data found',
                'data': {
                    'nama': request.POST.get('nama'),
                    'accuracy': accuracy,
                    'prediction': prediction[0],
                    'data_train': len(x_train),
                    'data_test': len(x_test),
                    'report': report,
                },
            })

def upload_dataset(request):
    if request.method == 'POST':
        if len(os.listdir('media/')) != 0:
            os.remove('media/' + os.listdir('media/')[-1])

        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            handle_uploaded_file(request.FILES['dataset'])
            return redirect('rekomendasi')
        else:
            return redirect('rekomendasi')
    else:
        return redirect('rekomendasi')


def delete_dataset(request):
    if request.method == 'POST':
        if len(os.listdir('media/')) != 0:
            os.remove('media/' + os.listdir('media/')[-1])
            return redirect('rekomendasi')
        else:
            return redirect('rekomendasi')
    else:
        return redirect('rekomendasi')

def bar_data(request):
    # if media folder is empty
    if len(os.listdir('media/')) == 0:
        return redirect('/')
    else:
        df = pd.read_csv('media/' + os.listdir('media/')[-1])
        last_col = df.iloc[:, -1].value_counts().to_dict()
        last_col = list(last_col.items())
        
        # label to array 
        label = []
        for i in range(len(last_col)):
            label.append(last_col[i][0])
        
        # data to array
        count = []
        for i in range(len(last_col)):
            count.append(last_col[i][1])
        
        # json
        last_col = {
            'label': label,
            'count': count,
        }

        
        # return json
        return JsonResponse(last_col, safe=False)