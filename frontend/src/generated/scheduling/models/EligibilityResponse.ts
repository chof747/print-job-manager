/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EligibilityFailure } from './EligibilityFailure';
export type EligibilityResponse = {
    eligible: boolean;
    blocked: boolean;
    failures: Array<EligibilityFailure>;
    satisfied: Array<EligibilityFailure>;
};
