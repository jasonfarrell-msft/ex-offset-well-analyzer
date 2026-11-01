using './registry.bicep'

param location = 'centralus'
param containerRegistryName = 'acrdrilladvisormx01'

param tags = {
  application: 'Drill Advisor'
  environment: 'poc'
  dataClassification: 'synthetic'
  SecurityControl: 'Ignore'
}
