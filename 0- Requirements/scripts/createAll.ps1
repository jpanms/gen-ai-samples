$SubscriptionId = '<your-subscription-id>'
$resourceGroupName = "jpan-genai-workshop"
$location = "australiaeast"

# Check if the Az module is installed
if (-not (Get-Module -ListAvailable -Name Az)) {
    Write-Output "Az module not found. Installing Az module..."
    Install-Module -Name Az -AllowClobber -Force -Scope CurrentUser
}

# Import the Az module
Import-Module Az
# Set subscription 
Set-AzContext -SubscriptionId $subscriptionId 
# Create a resource group
New-AzResourceGroup -Name $resourceGroupName -Location $location
# Deploy resources using the Bicep template
New-AzResourceGroupDeployment -ResourceGroupName $resourceGroupName -TemplateFile deployAll.bicep -WarningAction:SilentlyContinue
