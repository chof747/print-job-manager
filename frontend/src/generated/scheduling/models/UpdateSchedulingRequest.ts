/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferredPrinterAssignment } from './PreferredPrinterAssignment';
export type UpdateSchedulingRequest = {
    expectedVersion: number;
    priority?: number;
    dueDate?: (string | null);
    notes?: (string | null);
    tags?: Array<string>;
    printerAssignment?: (PreferredPrinterAssignment | null);
};

