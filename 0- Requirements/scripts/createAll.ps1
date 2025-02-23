$SubscriptionId = '89f07bef-2e3f-4ee3-abba-a38a0d048a9e'
$resourceGroupName = "jpan-genai-workshop"
$location = "australiaeast"

# Set subscription 
Set-AzContext -SubscriptionId $subscriptionId 
# Create a resource group
New-AzResourceGroup -Name $resourceGroupName -Location $location

New-AzResourceGroupDeployment -ResourceGroupName $resourceGroupName -TemplateFile deployAll.bicep -WarningAction:SilentlyContinue