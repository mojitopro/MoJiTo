"""
RENDER FREE TIER SOLUTION

Render free tier puts dynos to sleep after 15 min of inactivity.

SOLUCIONES:

1. CRON-JOB.ORG (Gratis - recomendado):
   - Ve a https://cron-job.org
   - Crea cuenta gratis
   - Crea un job:
     * URL: https://tu-servicio.onrender.com/api/status
     * Schedule: Every 10 minutes
   - Esto mantiene el dyno despierto

2. HEALTH CHECK EN RENDER:
   - Dashboard -> Your Service -> Health Check
   - Path: /api/status
   - Interval: 5 minutes
   - Timeout: 10 seconds

3. UPTIMEROBOT (Gratis):
   - https://uptimerobot.com
   - Crea monitor tipo "HTTPS"
   - Interval: 10 min
   - El ping mantiene activo el dyno

El worker de Python no funciona en Render Free porque
no permite procesos en background.
"""

import os

RENDER_URL = os.environ.get('RENDER_URL', 'https://tu-servicio.onrender.com')

print(__doc__)
print(f"\nURL configurada: {RENDER_URL}")