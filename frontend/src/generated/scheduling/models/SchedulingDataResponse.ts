/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferredPrinterAssignment } from './PreferredPrinterAssignment';
export type SchedulingDataResponse = {
    priority: number;
    dueDate?: (string | null);
    notes?: (string | null);
    tags?: (Array<string> | null);
    printerAssignment?: (PreferredPrinterAssignment | null);
};

