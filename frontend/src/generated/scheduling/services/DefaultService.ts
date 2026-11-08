/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CockpitResponse } from '../models/CockpitResponse';
import type { EligibilityRequest } from '../models/EligibilityRequest';
import type { EligibilityResponse } from '../models/EligibilityResponse';
import type { MaterialInventoryRequest } from '../models/MaterialInventoryRequest';
import type { PrinterCapabilitiesRequest } from '../models/PrinterCapabilitiesRequest';
import type { SchedulingJobResponse } from '../models/SchedulingJobResponse';
import type { UpdateSchedulingRequest } from '../models/UpdateSchedulingRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class DefaultService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Update Job Scheduling
     * @returns SchedulingJobResponse Successful Response
     * @throws ApiError
     */
    public updateJobSchedulingApiV1JobsJobIdSchedulingPatch({
        jobId,
        requestBody,
    }: {
        jobId: string,
        requestBody: UpdateSchedulingRequest,
    }): CancelablePromise<SchedulingJobResponse> {
        return this.httpRequest.request({
            method: 'PATCH',
            url: '/jobs/{job_id}/scheduling',
            path: {
                'job_id': jobId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Cockpit
     * @returns CockpitResponse Successful Response
     * @throws ApiError
     */
    public cockpitApiV1CockpitGet({
        diagnosticCode,
        material,
        minDurationSeconds,
        minPriority,
        dueBefore,
        tag,
        assignmentMode,
        maxFilamentWeightGrams,
        nozzleDiameter,
        maxDimensionX,
        maxDimensionY,
        maxDimensionZ,
        slicer,
        provenanceParser,
    }: {
        diagnosticCode?: (string | null),
        material?: (string | null),
        minDurationSeconds?: (number | null),
        minPriority?: (number | null),
        dueBefore?: (string | null),
        tag?: (string | null),
        assignmentMode?: (string | null),
        maxFilamentWeightGrams?: (number | null),
        nozzleDiameter?: (number | null),
        maxDimensionX?: (number | null),
        maxDimensionY?: (number | null),
        maxDimensionZ?: (number | null),
        slicer?: (string | null),
        provenanceParser?: (string | null),
    }): CancelablePromise<CockpitResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/cockpit',
            query: {
                'diagnosticCode': diagnosticCode,
                'material': material,
                'minDurationSeconds': minDurationSeconds,
                'minPriority': minPriority,
                'dueBefore': dueBefore,
                'tag': tag,
                'assignmentMode': assignmentMode,
                'maxFilamentWeightGrams': maxFilamentWeightGrams,
                'nozzleDiameter': nozzleDiameter,
                'maxDimensionX': maxDimensionX,
                'maxDimensionY': maxDimensionY,
                'maxDimensionZ': maxDimensionZ,
                'slicer': slicer,
                'provenanceParser': provenanceParser,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Job Detail
     * @returns SchedulingJobResponse Successful Response
     * @throws ApiError
     */
    public jobDetailApiV1JobsJobIdGet({
        jobId,
    }: {
        jobId: string,
    }): CancelablePromise<SchedulingJobResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/jobs/{job_id}',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Job Eligibility
     * Check trusted printer capabilities against inventory-owned availability.
     * @returns EligibilityResponse Successful Response
     * @throws ApiError
     */
    public jobEligibilityApiV1JobsJobIdEligibilityPost({
        jobId,
        requestBody,
    }: {
        jobId: string,
        requestBody: EligibilityRequest,
    }): CancelablePromise<EligibilityResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/jobs/{job_id}/eligibility',
            path: {
                'job_id': jobId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Put Printer
     * @returns any Successful Response
     * @throws ApiError
     */
    public putPrinterApiV1PrintersPrinterIdPut({
        printerId,
        requestBody,
    }: {
        printerId: string,
        requestBody: PrinterCapabilitiesRequest,
    }): CancelablePromise<Record<string, any>> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/printers/{printer_id}',
            path: {
                'printer_id': printerId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add Inventory Material
     * @returns any Successful Response
     * @throws ApiError
     */
    public addInventoryMaterialApiV1InventoryMaterialsPost({
        requestBody,
    }: {
        requestBody: MaterialInventoryRequest,
    }): CancelablePromise<Record<string, any>> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/inventory/materials',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
