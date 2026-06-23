Feature: H360TK Behave integration working

  Scenario: Basic Facility Creation
    Given I create a new facility with name "BasicFacility"


  Scenario: Seed a multi-tiered facility hierarchy safely
    Given The following facility exists:
      | name                  |
      | {run_id}             |
      | Northern Region       |
      | Apex Referral Hospital|


  Scenario: PLOP
    Given A top level Org Unit exists for the current run
    And An org unit exists in the current org unit with name "A"
    And An org unit exists in the current org unit with name "B"
    And An org unit exists in the current org unit with name "C"