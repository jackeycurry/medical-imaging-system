# -*- coding: utf-8 -*-
import requests
import json

# Test login
r = requests.post('http://localhost:8080/api/auth/login', json={'username': 'admin', 'password': '123456'})
print('Login:', r.status_code, r.json())

# Test create patient
data = {'name': '张三', 'gender': '男', 'age': 45, 'phone': '13800138000', 'disease': '肺炎', 'address': '北京'}
r = requests.post('http://localhost:8080/api/patients', json=data)
print('Create patient:', r.status_code, r.text)

# Test get patients
r = requests.get('http://localhost:8080/api/patients')
print('Get patients:', r.status_code, r.json())