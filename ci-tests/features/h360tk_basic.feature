Feature: H360TK Behave integration working

  Scenario: Basic Facility Creation
    Given I create a new facility with name "BasicFacility"


  Scenario: Seed a multi-tiered facility hierarchy safely
    Given The following facility exists:
      | name                  |
      | National Health Dept  |
      | Northern Region       |
      | Apex Referral Hospital|
