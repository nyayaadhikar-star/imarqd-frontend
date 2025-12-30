// Bicep placeholder sample
param location string = resourceGroup().location
param appName string = 'klyvo-api'

resource plan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: '${appName}-plan'
  location: location
  sku: {
    name: 'F1'
    tier: 'Free'
  }
}

resource app 'Microsoft.Web/sites@2022-03-01' = {
  name: appName
  location: location
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
  }
}

output appUrl string = 'https://${app.name}.azurewebsites.net'


