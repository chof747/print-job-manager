/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BuildVolumeRequest } from './BuildVolumeRequest';
export type PrinterCapabilitiesRequest = {
    enclosure: boolean;
    hardenedNozzle?: (boolean | null);
    nozzleDiameter?: (number | null);
    buildVolume?: (BuildVolumeRequest | null);
};
